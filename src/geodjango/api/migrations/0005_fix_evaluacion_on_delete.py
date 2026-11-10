"""Alinea las FK de `evaluacion` con el comportamiento real de la base.

Hallazgo de la validación de portabilidad (2026-09-08): `api/models.py` declaraba
ambas FK de `Evaluacion` con `on_delete=DO_NOTHING` (lo que Django genera por
defecto), pero la base de datos de desarrollo real las tiene con
`id_inmueble ON DELETE CASCADE` / `id_subindicador ON DELETE RESTRICT` -alguien
las corrigió a mano con SQL crudo en algún momento, y el modelo nunca se
actualizó para reflejarlo-. Una instalación nueva, migrada solo con Django,
quedaba con el comportamiento por defecto (NO ACTION) en vez del real.

`SeparateDatabaseAndState` actualiza el estado de Django (para que
`makemigrations` futuro no proponga revertir el cambio) sin depender de
`AlterField`, que Django omite en tablas `managed = False`. El bloque PL/pgSQL
busca el nombre real de cada constraint (varía entre instalaciones: Django y
un `ALTER TABLE` a mano no nombran las FK igual) y solo la reemplaza si el
`ON DELETE` no es ya el correcto -no-op seguro en la base real, que ya lo tiene
bien-.
"""

from django.db import migrations, models


_FIX_SQL = """
DO $$
DECLARE
    v_constraint text;
BEGIN
    SELECT conname INTO v_constraint
    FROM pg_constraint
    WHERE conrelid = 'evaluacion'::regclass
      AND contype = 'f'
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                           WHERE attrelid = 'evaluacion'::regclass AND attname = 'id_inmueble')]
      AND confdeltype <> 'c';
    IF v_constraint IS NOT NULL THEN
        EXECUTE format('ALTER TABLE evaluacion DROP CONSTRAINT %I', v_constraint);
        ALTER TABLE evaluacion ADD CONSTRAINT evaluacion_id_inmueble_fkey
            FOREIGN KEY (id_inmueble) REFERENCES inmuebles(id) ON DELETE CASCADE;
    END IF;

    SELECT conname INTO v_constraint
    FROM pg_constraint
    WHERE conrelid = 'evaluacion'::regclass
      AND contype = 'f'
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                           WHERE attrelid = 'evaluacion'::regclass AND attname = 'id_subindicador')]
      AND confdeltype <> 'r';
    IF v_constraint IS NOT NULL THEN
        EXECUTE format('ALTER TABLE evaluacion DROP CONSTRAINT %I', v_constraint);
        ALTER TABLE evaluacion ADD CONSTRAINT evaluacion_id_subindicador_fkey
            FOREIGN KEY (id_subindicador) REFERENCES sub_indicadores(id) ON DELETE RESTRICT;
    END IF;
END $$;
"""

_REVERSE_SQL = """
DO $$
DECLARE
    v_constraint text;
BEGIN
    SELECT conname INTO v_constraint FROM pg_constraint
    WHERE conrelid = 'evaluacion'::regclass AND contype = 'f'
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                           WHERE attrelid = 'evaluacion'::regclass AND attname = 'id_inmueble')];
    EXECUTE format('ALTER TABLE evaluacion DROP CONSTRAINT %I', v_constraint);
    ALTER TABLE evaluacion ADD CONSTRAINT evaluacion_id_inmueble_fkey
        FOREIGN KEY (id_inmueble) REFERENCES inmuebles(id);

    SELECT conname INTO v_constraint FROM pg_constraint
    WHERE conrelid = 'evaluacion'::regclass AND contype = 'f'
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                           WHERE attrelid = 'evaluacion'::regclass AND attname = 'id_subindicador')];
    EXECUTE format('ALTER TABLE evaluacion DROP CONSTRAINT %I', v_constraint);
    ALTER TABLE evaluacion ADD CONSTRAINT evaluacion_id_subindicador_fkey
        FOREIGN KEY (id_subindicador) REFERENCES sub_indicadores(id);
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_ensure_evaluacion_valor_column'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='evaluacion',
                    name='id_inmueble',
                    field=models.ForeignKey('api.Inmuebles', models.CASCADE, db_column='id_inmueble'),
                ),
                migrations.AlterField(
                    model_name='evaluacion',
                    name='id_subindicador',
                    field=models.ForeignKey('api.SubIndicadores', models.RESTRICT, db_column='id_subindicador'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(sql=_FIX_SQL, reverse_sql=_REVERSE_SQL),
            ],
        ),
    ]
