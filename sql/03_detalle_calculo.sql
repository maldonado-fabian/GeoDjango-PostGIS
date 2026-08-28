-- =============================================================================
-- postgisftw.detalle_calculo(amenaza_id) — detalle de riesgo por inmueble
-- =============================================================================
--
-- Reemplaza a la vista `public.detalle_calculo_incendio`, que tenía
-- `ind.amenaza_id = 1` escrito a mano y por lo tanto sólo servía para Incendio.
--
-- Va en el esquema `postgisftw` porque es el que pg_featureserv publica como
-- funciones. Queda disponible en:
--
--     http://localhost:9000/functions/postgisftw.detalle_calculo/items?amenaza_id=1
--
-- Tres diferencias respecto de la vista original:
--
--   1. La amenaza es un parámetro.
--   2. El filtro externo de inmuebles también se acota a la amenaza. Antes era
--      `EXISTS (SELECT 1 FROM evaluacion WHERE id_inmueble = i.id)` sin más, así
--      que un inmueble evaluado sólo para otra amenaza salía igual, con
--      `detalle_riesgo` en null.
--   3. El `JOIN clases` pasa a LEFT JOIN LATERAL con agregación. La vista unía
--      por `c.valor = e.valor`, y en Sismo hay sub-indicadores con varias clases
--      del mismo puntaje ("Tipo de fundaciones" tiene dos clases de valor 4,
--      "Muros de contención" tiene dos de valor 1, dos de 2 y dos de 3): ese JOIN
--      habría devuelto el sub-indicador repetido en el JSON. Al ser LEFT, además,
--      un valor sin clase definida ya no borra el sub-indicador del detalle.
--
-- La vista `public.detalle_calculo_incendio` se mantiene como envoltorio sobre
-- la función. Ni el mapa ni el API la usan ya, pero sigue publicada como
-- colección en pg_featureserv y puede haber proyectos QGIS apuntando a ella.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS postgisftw;

-- La vista de compatibilidad se apoya en la función: hay que soltarla antes de
-- poder redefinirla. Se vuelve a crear al final del archivo.
DROP VIEW IF EXISTS public.detalle_calculo_incendio;
DROP FUNCTION IF EXISTS postgisftw.detalle_calculo(integer);
DROP FUNCTION IF EXISTS postgisftw.detalle_calculo(integer, integer);

-- `inmueble_id` permite pedir un solo inmueble: el mapa lo usa para refrescar la
-- ficha después de editar una evaluación, sin recargar los 2.000 features.
CREATE FUNCTION postgisftw.detalle_calculo(amenaza_id integer DEFAULT 1,
                                           inmueble_id integer DEFAULT NULL)
RETURNS TABLE (
    id              integer,
    geom            geometry(MultiPolygon, 4326),
    direccion       character varying(255),
    rol_sii         character varying(25),
    manzana         character varying(50),
    predio          character varying(255),
    detalle_riesgo  jsonb
)
AS $$
    SELECT
        i.id,
        i.geom,
        i.direccion,
        i.rol_sii,
        i.manzana,
        i.predio,
        jsonb_build_object('indicadores', (
            SELECT jsonb_agg(jsonb_build_object(
                'indicador_id',     ind.id,
                'indicador_nombre', ind.nombre,
                'peso',             ind.peso,
                'riesgo_indicador', (
                    SELECT SUM(si.peso * e.valor::numeric) * ind.peso
                    FROM evaluacion e
                    JOIN sub_indicadores si ON e.id_subindicador = si.id
                    WHERE e.id_inmueble = i.id AND si.indicador_id = ind.id
                ),
                'sub_indicadores', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'sub_indicador_id',              si.id,
                        'sub_indicador_nombre',          si.nombre,
                        'peso_subindicador',             si.peso,
                        'valor',                         e.valor,
                        'clase',                         cl.nombre,
                        'riesgo_subindicador',           e.valor::numeric * si.peso,
                        'riesgo_subindicador_ponderado', e.valor::numeric * si.peso * ind.peso
                    ) ORDER BY si.id)
                    FROM evaluacion e
                    JOIN sub_indicadores si ON e.id_subindicador = si.id
                    LEFT JOIN LATERAL (
                        -- Varias clases pueden compartir puntaje: se agregan en
                        -- una sola etiqueta en vez de multiplicar la fila.
                        SELECT string_agg(c.nombre, ' / ' ORDER BY c.id) AS nombre
                        FROM clases c
                        WHERE c.sub_indicador_id = si.id AND c.valor = e.valor
                    ) cl ON TRUE
                    WHERE e.id_inmueble = i.id AND si.indicador_id = ind.id
                )
            ) ORDER BY ind.id)
            FROM indicadores ind
            WHERE ind.amenaza_id = detalle_calculo.amenaza_id
              AND EXISTS (
                  SELECT 1
                  FROM evaluacion e
                  JOIN sub_indicadores si ON e.id_subindicador = si.id
                  WHERE e.id_inmueble = i.id AND si.indicador_id = ind.id
              )
        )) AS detalle_riesgo
    FROM inmuebles i
    WHERE (detalle_calculo.inmueble_id IS NULL OR i.id = detalle_calculo.inmueble_id)
      AND EXISTS (
        SELECT 1
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind    ON si.indicador_id = ind.id
        WHERE e.id_inmueble = i.id
          AND ind.amenaza_id = detalle_calculo.amenaza_id
    );
$$
LANGUAGE sql STABLE PARALLEL SAFE;

COMMENT ON FUNCTION postgisftw.detalle_calculo(integer, integer) IS
    'Detalle de riesgo por inmueble para una amenaza. Publicada por pg_featureserv.';


-- Compatibilidad para consumidores externos (ver cabecera).
-- El geom se castea de vuelta al typmod original: al pasar por el RETURNS TABLE
-- de la función pierde el modificador, y sin él pg_featureserv no registra la
-- vista como colección espacial.
DROP VIEW IF EXISTS public.detalle_calculo_incendio;

CREATE VIEW public.detalle_calculo_incendio AS
SELECT id,
       geom::geometry(MultiPolygon, 4326) AS geom,
       direccion, rol_sii, manzana, predio, detalle_riesgo
FROM postgisftw.detalle_calculo(
    (SELECT id FROM amenazas WHERE nombre = 'Incendio')
);


-- =============================================================================
-- Verificación
-- =============================================================================
--
-- Índices contra el Excel — 00001-00007 debe dar 1,675 en Sismo y 1,70 en Incendio:
--
--   SELECT rol_sii, ROUND((
--       SELECT SUM((ind->>'riesgo_indicador')::numeric)
--       FROM jsonb_array_elements(detalle_riesgo->'indicadores') ind), 4)
--   FROM postgisftw.detalle_calculo(
--       (SELECT id FROM amenazas WHERE nombre='Sismo'))
--   WHERE rol_sii = '00001-00007';
--
-- Ningún sub-indicador debe aparecer repetido dentro de un mismo indicador:
--
--   SELECT rol_sii, sub->>'sub_indicador_nombre' AS sub_ind, COUNT(*)
--   FROM postgisftw.detalle_calculo(
--            (SELECT id FROM amenazas WHERE nombre='Sismo')),
--        jsonb_array_elements(detalle_riesgo->'indicadores') ind,
--        jsonb_array_elements(ind->'sub_indicadores') sub
--   GROUP BY 1, 2 HAVING COUNT(*) > 1;
-- =============================================================================
