"""Garantiza que `evaluacion.valor` exista, sin importar el punto de partida.

Hallazgo de la validación de portabilidad (2026-09-08): `0003_evaluacion_add_valor`
usa `AddField`, que Django omite en tiempo de ejecución porque `Evaluacion` quedó
`managed = False` desde `0002_alter_evaluacion_options`. En la base de desarrollo
la columna existe porque alguien la agregó a mano con SQL crudo -la migración 0003
nunca la creó realmente-, así que en cualquier instalación nueva `migrate` termina
"aplicado" sin que la columna exista.

`RunSQL` sí ejecuta en tablas no administradas (a diferencia de `AddField`), y
`ADD COLUMN IF NOT EXISTS` lo vuelve un no-op seguro donde la columna ya está.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_evaluacion_add_valor'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE evaluacion ADD COLUMN IF NOT EXISTS valor integer NOT NULL DEFAULT 0;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
