-- =============================================================================
-- Amenaza SISMO — catálogo de indicadores, sub-indicadores y clases
-- =============================================================================
--
-- Fuentes:
--   · media/guia de evaluación/Manual de llenado.pdf — Tabla 2, pp. 36-40
--     (nombres de indicadores, sub-indicadores y textos de las clases)
--   · media/bases de datos/sismo.xlsx — filas 3-6 (pesos)
--
-- SOBRE LOS PESOS —————————————————————————————————————————————————————————————
-- El manual y el Excel no coinciden en cinco pesos. Se cargan los del EXCEL,
-- porque son los únicos que reproducen los índices que el propio Excel trae
-- precalculados (columnas L, P, V, AB, AG) para las 1.224 filas evaluadas:
--
--   Sub-indicador                  Manual   Excel   Filas que reproduce
--   Tipología constructiva          0.3      0.4    Excel 1224/1224, Manual 518/1224
--   Calidad de la construcción      0.3      0.2      "
--   Estructura de entrepiso         0.2      0.25     "
--   Techumbres                      0.2      0.15     "
--   N° de plantas habitables        0.2      0.3    Excel 1224/1224, Manual 0/1224
--
-- Además, los pesos del manual para "Regularidad" suman 0,9 en vez de 1,0, lo
-- que confirma que la tabla impresa tiene una errata. El resto de los pesos
-- coincide en ambas fuentes.
--
-- SOBRE LAS CLASES ————————————————————————————————————————————————————————————
-- · "Número de plantas habitables" usa escala directa (1 planta=1 ... 4+=4),
--   igual que Incendio. El manual mapea "3 plantas"->2 y no define clase con
--   valor 3, pero el Excel trae 200 filas con valor 3 que quedarían sin etiqueta.
-- · "Tipo de fundaciones" (5 clases), "Muros de contención" (7) y "Elementos no
--   estructurales..." (5) tienen varias clases con el mismo puntaje. Es correcto:
--   el UNIQUE de `clases` es (sub_indicador_id, nombre), no (sub_indicador_id,
--   valor). La función public.detalle_calculo() las agrega en vez de duplicar
--   la fila del sub-indicador (ver 03_detalle_calculo.sql).
-- · Los rangos de "Pendiente del terreno" están normalizados: el manual imprime
--   "0 < p >= 20%", "41 < p> 60%" y "61 % < p", con los operadores invertidos.
--
-- Idempotente: se puede re-ejecutar sin duplicar.
-- =============================================================================

BEGIN;

-- ── 1. Amenaza ───────────────────────────────────────────────────────────────

INSERT INTO amenazas (nombre, descripcion, fecha_creacion)
VALUES ('Sismo',
        'Vulnerabilidad sísmica de los inmuebles del área histórica de Valparaíso',
        NOW())
ON CONFLICT (nombre) DO NOTHING;


-- ── 2. Indicadores ───────────────────────────────────────────────────────────

INSERT INTO indicadores (amenaza_id, nombre, descripcion, peso, activo, fecha_creacion)
SELECT a.id, v.nombre, v.descripcion, v.peso, TRUE, NOW()
FROM amenazas a
CROSS JOIN (VALUES
    ('Sistema constructivo',
     'Características constructivas y estructurales más influyentes en el comportamiento sísmico de la estructura.',
     0.25),
    ('Regularidad',
     'Regularidad geométrica en planta y en elevación del edificio, y número de plantas habitables.',
     0.15),
    ('Emplazamiento y tipo de suelo',
     'Interacción del edificio con el terreno: suelo, pendiente, fundaciones, muros de contención y agrupamiento.',
     0.10),
    ('Grado de daño',
     'Grado de daño de los principales componentes estructurales del inmueble.',
     0.20),
    ('Estado de conservación',
     'Situación actual del edificio considerando el daño general y las intervenciones posteriores.',
     0.20),
    ('Elementos no estructurales',
     'Presencia y estabilidad de elementos no estructurales proyectados que pudieran desprenderse sobre la vía pública.',
     0.10)
) AS v(nombre, descripcion, peso)
WHERE a.nombre = 'Sismo'
ON CONFLICT (amenaza_id, nombre) DO NOTHING;


-- ── 3. Sub-indicadores ───────────────────────────────────────────────────────

INSERT INTO sub_indicadores (indicador_id, nombre, peso, activo, fecha_creacion)
SELECT i.id, v.sub, v.peso, TRUE, NOW()
FROM (VALUES
    ('Sistema constructivo',          'Tipología constructiva',                               0.4000),
    ('Sistema constructivo',          'Calidad de la construcción',                           0.2000),
    ('Sistema constructivo',          'Estructura de entrepiso',                              0.2500),
    ('Sistema constructivo',          'Techumbres',                                           0.1500),

    ('Regularidad',                   'Regularidad en planta',                                0.4000),
    ('Regularidad',                   'Regularidad en elevación',                             0.3000),
    ('Regularidad',                   'Número de plantas habitables',                         0.3000),

    ('Emplazamiento y tipo de suelo', 'Tipo de suelo',                                        0.2000),
    ('Emplazamiento y tipo de suelo', 'Pendiente del terreno',                                0.2000),
    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones',                                  0.2000),
    ('Emplazamiento y tipo de suelo', 'Muros de contención',                                  0.1000),
    ('Emplazamiento y tipo de suelo', 'Sistema de agrupamiento',                              0.3000),

    ('Grado de daño',                 'Muros de carga',                                       0.3000),
    ('Grado de daño',                 'Estructuras de entrepiso',                             0.3000),
    ('Grado de daño',                 'Techumbre',                                            0.1000),
    ('Grado de daño',                 'Elementos secundarios del sistema constructivo',       0.1000),
    ('Grado de daño',                 'Fundaciones y muros de contención',                    0.2000),

    ('Estado de conservación',        'Estado de conservación general',                       1.0000),

    ('Elementos no estructurales',    'Elementos no estructurales de la fachada y techumbre', 1.0000)
) AS v(ind, sub, peso)
JOIN amenazas   a ON a.nombre = 'Sismo'
JOIN indicadores i ON i.amenaza_id = a.id AND i.nombre = v.ind
ON CONFLICT (indicador_id, nombre) DO NOTHING;


-- ── 4. Clases ────────────────────────────────────────────────────────────────

-- `nombre` es varchar(100) y es la etiqueta que muestra la ficha del mapa:
-- va la versión corta. `descripcion` lleva el texto íntegro del manual.
-- Mismo criterio que el catálogo de Incendio.

INSERT INTO clases (sub_indicador_id, nombre, valor, descripcion, activo, fecha_creacion)
SELECT si.id, v.clase, v.valor, v.descripcion, TRUE, NOW()
FROM (VALUES
    -- 4.1 Sistema constructivo ------------------------------------------------
    ('Sistema constructivo', 'Tipología constructiva', 'Hormigón, acero o albañilería armada (post-1972)', 1,
     'Edificios de hormigón armado, acero o albañilería de ladrillo armado construidos después del año 1972.'),
    ('Sistema constructivo', 'Tipología constructiva', 'Hormigón, acero o albañilería armada (pre-1972)', 2,
     'Edificios de hormigón armado, acero/hierro forjado o albañilería de ladrillo armado construidos antes del año 1972.'),
    ('Sistema constructivo', 'Tipología constructiva', 'Entramado de madera o mixto (pre-1972)', 3,
     'Edificios de entramado de madera o edificios mixtos de entramado de madera y albañilería no reforzada anteriores al año 1972.'),
    ('Sistema constructivo', 'Tipología constructiva', 'Material ligero o diseño sismorresistente deficiente', 4,
     'Construcciones de material ligero o construcciones con un diseño sismorresistente deficiente (por ejemplo, muros de carga sin arriostramientos).'),

    ('Sistema constructivo', 'Calidad de la construcción', 'Muy buena', 1, 'Calidad de la construcción muy buena'),
    ('Sistema constructivo', 'Calidad de la construcción', 'Buena',     2, 'Calidad de la construcción buena'),
    ('Sistema constructivo', 'Calidad de la construcción', 'Regular',   3, 'Calidad de la construcción regular'),
    ('Sistema constructivo', 'Calidad de la construcción', 'Mala',      4, 'Calidad de la construcción mala'),

    ('Sistema constructivo', 'Estructura de entrepiso', 'Rígidas y bien conectadas', 1,
     'Estructuras de entrepiso rígidas y bien conectadas.'),
    ('Sistema constructivo', 'Estructura de entrepiso', 'Semirrígidas y bien conectadas', 2,
     'Estructuras de entrepiso semirrígidas y bien conectadas.'),
    ('Sistema constructivo', 'Estructura de entrepiso', 'Semirrígidas mal conectadas o con daño localizado', 3,
     'Estructuras de entrepiso semirrígidas y mal conectadas o con daño localizado en las conexiones.'),
    ('Sistema constructivo', 'Estructura de entrepiso', 'Flexibles y/o mal conectadas', 4,
     'Estructuras de entrepiso flexibles (sistemas de viguetas con una sola capa de entablado) de cualquier naturaleza y/o mal conectados o con daño localizado en las conexiones.'),

    ('Sistema constructivo', 'Techumbres', 'Losa de hormigón o cerchas bien amarradas', 1,
     'Losas de hormigón armado, cerchas de madera o acero (1 o 2 aguas) bien amarradas a los muros de carga a través de las vigas horizontales.'),
    ('Sistema constructivo', 'Techumbres', 'Cerchas deficientemente atadas', 2,
     'Cerchas de madera o acero (1 o 2 aguas) deficientemente atadas a los muros de carga (con daño localizado en las conexiones).'),
    ('Sistema constructivo', 'Techumbres', 'Cerchas mal atadas, con daño generalizado', 3,
     'Cerchas de madera a una o dos aguas, mal atadas a los muros de carga (con daño generalizado en las conexiones).'),
    ('Sistema constructivo', 'Techumbres', 'Cerchas sin vigas horizontales de amarre', 4,
     'Cerchas de madera (tijerales) tipo par e hilera o par y picaderos (sin vigas horizontales que las aten a los muros de carga).'),

    -- 4.2 Regularidad ---------------------------------------------------------
    ('Regularidad', 'Regularidad en planta', 'Muy regular',   1, 'Planta muy regular'),
    ('Regularidad', 'Regularidad en planta', 'Regular',       2, 'Planta regular'),
    ('Regularidad', 'Regularidad en planta', 'Irregular',     3, 'Planta irregular'),
    ('Regularidad', 'Regularidad en planta', 'Muy irregular', 4, 'Planta muy irregular'),

    ('Regularidad', 'Regularidad en elevación', 'Muy regular en terreno plano', 1, 'Elevación muy regular, en terreno plano'),
    ('Regularidad', 'Regularidad en elevación', 'Regular en pendiente',         2, 'Elevación regular, en pendiente'),
    ('Regularidad', 'Regularidad en elevación', 'Irregular',                    3, 'Elevación irregular'),
    ('Regularidad', 'Regularidad en elevación', 'Muy irregular',                4, 'Elevación muy irregular'),

    -- Escala directa: ver nota de cabecera.
    ('Regularidad', 'Número de plantas habitables', '1 planta',        1, 'Una planta habitable'),
    ('Regularidad', 'Número de plantas habitables', '2 plantas',       2, 'Dos plantas habitables'),
    ('Regularidad', 'Número de plantas habitables', '3 plantas',       3, 'Tres plantas habitables'),
    ('Regularidad', 'Número de plantas habitables', '4 plantas o más', 4, 'Cuatro o más plantas habitables'),

    -- 4.3 Emplazamiento y tipo de suelo ---------------------------------------
    ('Emplazamiento y tipo de suelo', 'Tipo de suelo', 'Roca',              1, 'Roca (roca intrusiva).'),
    ('Emplazamiento y tipo de suelo', 'Tipo de suelo', 'Terreno compacto',  2, 'Terreno compacto (depósitos coluviales).'),
    ('Emplazamiento y tipo de suelo', 'Tipo de suelo', 'Terreno suelto',    3, 'Terreno suelto (depósitos coluviales).'),
    ('Emplazamiento y tipo de suelo', 'Tipo de suelo', 'Relleno artificial', 4, 'Relleno artificial.'),

    ('Emplazamiento y tipo de suelo', 'Pendiente del terreno', 'Terreno plano o con poco desnivel', 1, 'Terreno plano o con poco desnivel (0 < p ≤ 20%).'),
    ('Emplazamiento y tipo de suelo', 'Pendiente del terreno', 'Pendiente 21% – 40%',               2, 'Pendiente entre 21% y 40%.'),
    ('Emplazamiento y tipo de suelo', 'Pendiente del terreno', 'Pendiente 41% – 60%',               3, 'Pendiente entre 41% y 60%.'),
    ('Emplazamiento y tipo de suelo', 'Pendiente del terreno', 'Pendiente sobre 61%',               4, 'Pendiente superior al 61%.'),

    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones', 'Zapata de hormigón o albañilería armada', 1,
     'Fundaciones tipo zapata corrida o aislada de hormigón o albañilería armada con o sin diferencia de nivel entre las fundaciones.'),
    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones', 'Zapata de albañilería no reforzada, desnivel bajo 1 m', 2,
     'Fundaciones tipo zapata corrida o aisladas, de albañilería de ladrillo no reforzada con niveles inferiores a 1 m. Basamentos o subterráneos de mampostería en piedra y/o albañilería de ladrillo con desniveles inferiores a 1 m.'),
    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones', 'Pilotes o pilares, desnivel bajo 1 m', 3,
     'Fundaciones tipo pilotes o pilares con diferencia de nivel entre fundaciones inferiores a 1 m.'),
    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones', 'Pilotes o pilares no reforzados, desnivel sobre 1 m', 4,
     'Fundaciones de tipo pilotes o pilares (zapatas aisladas) de albañilería de ladrillo no reforzado, madera o acero con diferencia de nivel entre fundaciones superiores a 1 m.'),
    ('Emplazamiento y tipo de suelo', 'Tipo de fundaciones', 'Sin fundaciones', 4,
     'Edificios sin fundaciones.'),

    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Muro de hormigón bien ejecutado', 1,
     'Muro de contención de hormigón armado o proyectado bien ejecutado/conservado (muro de gravedad, hincado, anclado, etc.).'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Terreno plano, no requiere contención', 1,
     'Edificio en terreno plano (no se requiere contención).'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Muro de mampostería bien ejecutado', 2,
     'Muro de contención de mampostería (muro de gravedad, hincado o anclado) o mallado bien ejecutado/conservado.'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Muro de configuración mixta', 2,
     'Muro de contención con configuración mixta: mampostería-hormigón proyectado o armado.'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Muro mal ejecutado o conservado', 3,
     'Muro de contención de mampostería, hormigón u otro material/tipología mal ejecutada/conservado (muro de gravedad, hincado, anclado o mallado).'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Roca vista sin muro de contención', 3,
     'Roca vista sin muro de contención.'),
    ('Emplazamiento y tipo de suelo', 'Muros de contención', 'Terreno suelto sin muro de contención', 4,
     'Terreno suelto sin muro de contención.'),

    ('Emplazamiento y tipo de suelo', 'Sistema de agrupamiento', 'Continuo', 1, 'Continuo.'),
    ('Emplazamiento y tipo de suelo', 'Sistema de agrupamiento', 'Separado', 2, 'Separado.'),
    ('Emplazamiento y tipo de suelo', 'Sistema de agrupamiento', 'Pareado',  3, 'Pareado.'),
    ('Emplazamiento y tipo de suelo', 'Sistema de agrupamiento', 'Aislado',  4, 'Aislado: no comparte muros medianeros.'),

    -- 4.4 Grado de daño -------------------------------------------------------
    ('Grado de daño', 'Muros de carga', 'Nulo o leve', 1, 'Daño nulo o leve en los muros de carga'),
    ('Grado de daño', 'Muros de carga', 'Moderado',    2, 'Daño moderado en los muros de carga'),
    ('Grado de daño', 'Muros de carga', 'Medio',       3, 'Daño medio en los muros de carga'),
    ('Grado de daño', 'Muros de carga', 'Severo',      4, 'Daño severo en los muros de carga'),

    ('Grado de daño', 'Estructuras de entrepiso', 'Nulo o leve', 1, 'Daño nulo o leve en las estructuras de entrepiso'),
    ('Grado de daño', 'Estructuras de entrepiso', 'Moderado',    2, 'Daño moderado en las estructuras de entrepiso'),
    ('Grado de daño', 'Estructuras de entrepiso', 'Medio',       3, 'Daño medio en las estructuras de entrepiso'),
    ('Grado de daño', 'Estructuras de entrepiso', 'Severo',      4, 'Daño severo en las estructuras de entrepiso'),

    ('Grado de daño', 'Techumbre', 'Nulo o leve', 1, 'Daño nulo o leve en la techumbre'),
    ('Grado de daño', 'Techumbre', 'Moderado',    2, 'Daño moderado en la techumbre'),
    ('Grado de daño', 'Techumbre', 'Medio',       3, 'Daño medio en la techumbre'),
    ('Grado de daño', 'Techumbre', 'Severo',      4, 'Daño severo en la techumbre'),

    ('Grado de daño', 'Elementos secundarios del sistema constructivo', 'Nulo o leve', 1, 'Daño nulo o leve en los elementos secundarios del sistema constructivo'),
    ('Grado de daño', 'Elementos secundarios del sistema constructivo', 'Moderado',    2, 'Daño moderado en los elementos secundarios del sistema constructivo'),
    ('Grado de daño', 'Elementos secundarios del sistema constructivo', 'Medio',       3, 'Daño medio en los elementos secundarios del sistema constructivo'),
    ('Grado de daño', 'Elementos secundarios del sistema constructivo', 'Severo',      4, 'Daño severo en los elementos secundarios del sistema constructivo'),

    ('Grado de daño', 'Fundaciones y muros de contención', 'Nulo o leve', 1, 'Daño nulo o leve en las fundaciones y muros de contención'),
    ('Grado de daño', 'Fundaciones y muros de contención', 'Moderado',    2, 'Daño moderado en las fundaciones y muros de contención'),
    ('Grado de daño', 'Fundaciones y muros de contención', 'Medio',       3, 'Daño medio en las fundaciones y muros de contención'),
    ('Grado de daño', 'Fundaciones y muros de contención', 'Severo',      4, 'Daño severo en las fundaciones y muros de contención'),

    -- 4.5 Estado de conservación ----------------------------------------------
    ('Estado de conservación', 'Estado de conservación general', 'Bueno o aceptable',  1, 'Estado de conservación bueno o aceptable'),
    ('Estado de conservación', 'Estado de conservación general', 'Regular',            2, 'Estado de conservación regular'),
    ('Estado de conservación', 'Estado de conservación general', 'Malo',               3, 'Estado de conservación malo'),
    ('Estado de conservación', 'Estado de conservación general', 'Muy malo o ruinoso', 4, 'Estado de conservación muy malo o ruinoso'),

    -- 4.6 Elementos no estructurales ------------------------------------------
    ('Elementos no estructurales', 'Elementos no estructurales de la fachada y techumbre', 'Sin elementos proyectados o ligeros bien conectados', 1,
     'Edificios sin elementos proyectados en la fachada o con elementos pequeños y/o ligeros bien conectados a la estructura principal.'),
    ('Elementos no estructurales', 'Elementos no estructurales de la fachada y techumbre', 'Elementos ligeros deficientemente conectados', 2,
     'Elementos pequeños y/o ligeros en la fachada deficientemente conectados a la estructura.'),
    ('Elementos no estructurales', 'Elementos no estructurales de la fachada y techumbre', 'Elementos pesados bien conectados', 2,
     'Elementos de gran tamaño/pesados bien conectados a la estructura principal de la fachada.'),
    ('Elementos no estructurales', 'Elementos no estructurales de la fachada y techumbre', 'Elementos pesados mal conectados o deteriorados', 3,
     'Elementos de gran tamaño o pesados mal conectados a la estructura principal de la fachada o con sus conexiones visiblemente deterioradas.'),
    ('Elementos no estructurales', 'Elementos no estructurales de la fachada y techumbre', 'Elementos pesados añadidos posteriormente', 4,
     'Elementos de gran tamaño que fueron añadidos posteriormente a la estructura y que tienen sus conexiones mal ejecutadas o visiblemente deterioradas.')
) AS v(ind, sub, clase, valor, descripcion)
JOIN amenazas        a  ON a.nombre = 'Sismo'
JOIN indicadores     i  ON i.amenaza_id = a.id AND i.nombre = v.ind
JOIN sub_indicadores si ON si.indicador_id = i.id AND si.nombre = v.sub
ON CONFLICT (sub_indicador_id, nombre) DO NOTHING;

COMMIT;


-- =============================================================================
-- Verificación
-- =============================================================================
--
-- Cada indicador debe sumar 1.0000 en sus sub-indicadores:
--
--   SELECT i.nombre, SUM(si.peso) AS suma
--   FROM sub_indicadores si
--   JOIN indicadores i ON si.indicador_id = i.id
--   JOIN amenazas    a ON i.amenaza_id = a.id
--   WHERE a.nombre = 'Sismo'
--   GROUP BY i.nombre;
--
-- Los indicadores deben sumar 1.00:
--
--   SELECT SUM(i.peso) FROM indicadores i
--   JOIN amenazas a ON i.amenaza_id = a.id WHERE a.nombre = 'Sismo';
--
-- Conteos esperados: 6 indicadores, 19 sub-indicadores, 81 clases.
-- =============================================================================
