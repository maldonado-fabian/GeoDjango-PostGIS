# SQL de la plataforma

Scripts que se aplican a mano sobre PostGIS. Van fuera de las migraciones de
Django porque las tablas del dominio son `managed = False` (ver `api/models.py`):
Django las consulta pero no las administra.

Todos son idempotentes.

## Orden de aplicación

| Archivo | Qué hace |
|---|---|
| *(no versionado)* | Catálogo de **Incendio**. Se pobló antes de que estos scripts existieran; la base ya lo tiene. |
| `02_amenaza_sismo.sql` | Catálogo de **Sismo**: 6 indicadores, 19 sub-indicadores, 81 clases. |
| `03_detalle_calculo.sql` | `postgisftw.detalle_calculo(amenaza_id, inmueble_id)`, la función que alimenta el mapa. Reemplaza a la vista `detalle_calculo_incendio`, que tenía la amenaza fija. |

```sh
docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/02_amenaza_sismo.sql

docker exec -i geodjango-docker-postgis-1 \
  psql -U postgres -d GRD_Docker -v ON_ERROR_STOP=1 < sql/03_detalle_calculo.sql

# pg_featureserv cachea el catálogo al arrancar
docker restart pg_featureserv
```

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
