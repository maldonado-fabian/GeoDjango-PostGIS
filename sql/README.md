# SQL de la plataforma

Scripts que se aplican a mano sobre PostGIS. Van fuera de las migraciones de
Django porque las tablas del dominio son `managed = False` (ver `api/models.py`):
Django las consulta pero no las administra.

Todos son idempotentes.

## Orden de aplicación

**`00_schema.sql` es nuevo (2026-09-08) y va primero, antes que `manage.py migrate`.**
Hasta esa fecha, `amenazas`/`indicadores`/`sub_indicadores`/`clases`/`inmuebles` no
tenían ningún `CREATE TABLE` versionado en ningún lado del repositorio — una
instalación nueva no podía ni siquiera terminar de migrar (`0001_Evaluacion` falla
con `relation "inmuebles" does not exist`, porque esa migración crea `evaluacion`
con una FK hacia una tabla que nadie había creado). Encontrado y corregido durante
la validación de portabilidad ISO/IEC 25010 de la memoria.

| Archivo | Qué hace |
|---|---|
| `00_schema.sql` | `CREATE TABLE` de las 5 tablas de dominio. **Va antes que `manage.py migrate`.** |
| `01_amenaza_incendio.sql` | Catálogo de **Incendio**: 4 indicadores, 19 sub-indicadores. |
| `02_amenaza_sismo.sql` | Catálogo de **Sismo**: 6 indicadores, 19 sub-indicadores, 81 clases. |
| `03_detalle_calculo.sql` | `postgisftw.detalle_calculo(amenaza_id, inmueble_id)`, la función que alimenta el mapa. Reemplaza a la vista `detalle_calculo_incendio`, que tenía la amenaza fija. |

```sh
docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/00_schema.sql

docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/01_amenaza_incendio.sql

docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/02_amenaza_sismo.sql

# recién acá: manage.py migrate (crea `evaluacion`, ya con inmuebles/sub_indicadores existiendo)

docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/03_detalle_calculo.sql

# pg_featureserv cachea el catálogo al arrancar
docker restart pg_featureserv
```

También hacía falta `src/geodjango/geodjango/.env` (no versionado, sin
`.env.example` hasta ahora — copiar `.env.example` del mismo directorio) y correr
`manage.py create_roles` a mano; `docker-compose.yml` ya encadena `migrate` +
`create_roles` antes de `runserver`, pero eso no cubre este archivo ni los de
`sql/*_amenaza_*.sql`, que siguen sin automatizarse (ver nota de cabecera de este
mismo README sobre por qué van fuera de las migraciones de Django).

## Cargar las evaluaciones de una amenaza

El catálogo (indicadores, sub-indicadores, clases) viene de estos SQL; la
evaluación por inmueble viene del Excel de terreno, en dos pasos:

```sh
# 1. Excel -> CSV. Detecta las columnas de sub-indicador por la fila de pesos,
#    así que no hay listas de columnas escritas a mano.
python3 scripts/excel_a_csv.py "src/geodjango/media/bases de datos/sismo.xlsx" datos_sismo.csv

# 2. CSV -> tabla evaluacion. --dry-run valida y reporta sin escribir.
docker cp datos_sismo.csv geodjango-docker-django-1:/tmp/
docker exec geodjango-docker-django-1 \
  python3 src/geodjango/manage.py cargar_evaluaciones /tmp/datos_sismo.csv \
          --amenaza Sismo --dry-run
```

El comando es un upsert: re-ejecutarlo actualiza en vez de duplicar. Rechaza y
reporta los valores del Excel que no correspondan a ninguna clase definida —en
Sismo son 21: `E`, `E.P` en "Tipología constructiva" y un `5` fuera de escala en
"Elementos secundarios del sistema constructivo".

## Agregar la próxima amenaza

Deslizamiento de tierra y Graffiti vandálico usan el mismo formato de Excel y la
misma estructura en el manual, así que el camino es:

1. Copiar `02_amenaza_sismo.sql`, reemplazar indicadores, sub-indicadores y clases
   con los de la Tabla correspondiente del manual de llenado.
2. Verificar que los pesos sumen 1 (las queries están al pie de ese archivo) y
   **contrastarlos contra los totales precalculados del Excel** — en Sismo, cinco
   pesos del manual no coincidían con los del Excel y ganaron los del Excel.
3. Convertir y cargar el Excel con los dos comandos de arriba.

No hay nada más que tocar: el API y el mapa resuelven la amenaza por parámetro.
