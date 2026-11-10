-- ============================================
-- SCRIPT COMPLETO PARA AMENAZA DE INCENDIO
-- Provisto por el usuario (fabian) el 2026-09-08 para la re-prueba de
-- portabilidad con datos reales. Mismo patrón que sql/02_amenaza_sismo.sql
-- del repositorio, pero para Incendio (que no tenía ningún script versionado).
-- ============================================

BEGIN;

INSERT INTO Amenazas (nombre, descripcion) 
VALUES ('Incendio', 'Amenaza relacionada con riesgo de incendio en inmuebles')
ON CONFLICT (nombre) DO NOTHING;

DO $$
DECLARE
    v_amenaza_id INTEGER;
    v_indicador_id INTEGER;
    v_sub1_id INTEGER;
    v_sub2_id INTEGER;
    v_sub3_id INTEGER;
    v_sub4_id INTEGER;
    v_sub5_id INTEGER;
BEGIN
    SELECT id INTO v_amenaza_id FROM Amenazas WHERE nombre = 'Incendio';
    
    INSERT INTO Indicadores (amenaza_id, nombre, descripcion, peso) 
    VALUES (v_amenaza_id, 'Intrínseco del inmueble', 'Características constructivas del inmueble', 0.3)
    ON CONFLICT (amenaza_id, nombre) DO NOTHING
    RETURNING id INTO v_indicador_id;
    
    IF v_indicador_id IS NULL THEN
        SELECT id INTO v_indicador_id FROM Indicadores 
        WHERE amenaza_id = v_amenaza_id AND nombre = 'Intrínseco del inmueble';
    END IF;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Materialidad estructural', 'Tipo de material estructural principal', 0.3)
    RETURNING id INTO v_sub1_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Materialidad revestimiento', 'Tipo de material de revestimiento exterior', 0.1)
    RETURNING id INTO v_sub2_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Número de plantas habitables', 'Cantidad de plantas del inmueble', 0.1)
    RETURNING id INTO v_sub3_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Sistema de agrupamiento', 'Grado de agrupamiento con edificaciones colindantes', 0.2)
    RETURNING id INTO v_sub4_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Estado de conservación general', 'Estado general de conservación del inmueble', 0.3)
    RETURNING id INTO v_sub5_id;
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub1_id, 'Hormigón armado o albañilería', 1, 'Estructura de hormigón armado o albañilería'),
    (v_sub1_id, 'Acero o hierro forjado', 2, 'Estructura de acero o hierro forjado'),
    (v_sub1_id, 'Entramado de madera', 4, 'Estructura de entramado de madera');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub2_id, 'Estuco de cemento o tierra', 1, 'Revestimiento de estuco de cemento o tierra'),
    (v_sub2_id, 'Vidrio', 2, 'Revestimiento de vidrio'),
    (v_sub2_id, 'Plancha metálica', 3, 'Revestimiento de plancha metálica'),
    (v_sub2_id, 'Madera', 4, 'Revestimiento de madera');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub3_id, '1 planta', 1, 'Inmueble de 1 planta habitable'),
    (v_sub3_id, '2 plantas', 2, 'Inmueble de 2 plantas habitables'),
    (v_sub3_id, '3 plantas', 3, 'Inmueble de 3 plantas habitables'),
    (v_sub3_id, '4 plantas o más', 4, 'Inmueble de 4 o más plantas habitables');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub4_id, 'Aislado o Separado', 1, 'Aislado (no comparte muros medianeros) o Separado (distante menos de 1m, no comparte muros medianeros)'),
    (v_sub4_id, 'Pareado', 2, 'Comparte solo una pared'),
    (v_sub4_id, 'Continuo 2 paredes', 3, 'Comparte dos paredes'),
    (v_sub4_id, 'Continuo 3 paredes', 4, 'Comparte tres paredes');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub5_id, 'Bueno o aceptable', 1, 'Estado de conservación bueno o aceptable'),
    (v_sub5_id, 'Regular', 2, 'Estado de conservación regular'),
    (v_sub5_id, 'Malo', 3, 'Estado de conservación malo'),
    (v_sub5_id, 'Muy malo o ruinoso', 4, 'Estado de conservación muy malo o ruinoso');
    
    RAISE NOTICE 'Indicador "Intrínseco del inmueble" creado con ID: %', v_indicador_id;
END $$;

DO $$
DECLARE
    v_amenaza_id INTEGER;
    v_indicador_id INTEGER;
    v_sub1_id INTEGER;
    v_sub2_id INTEGER;
    v_sub3_id INTEGER;
	v_sub4_id INTEGER;
BEGIN
    SELECT id INTO v_amenaza_id FROM Amenazas WHERE nombre = 'Incendio';
    
    INSERT INTO Indicadores (amenaza_id, nombre, descripcion, peso) 
    VALUES (v_amenaza_id, 'Uso y ocupación', 'Indicador relacionado con el uso y ocupación del inmueble', 0.2)
    ON CONFLICT (amenaza_id, nombre) DO NOTHING
    RETURNING id INTO v_indicador_id;
    
    IF v_indicador_id IS NULL THEN
        SELECT id INTO v_indicador_id FROM Indicadores 
        WHERE amenaza_id = v_amenaza_id AND nombre = 'Uso y ocupación';
    END IF;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Uso del inmueble', 'Tipo de uso y nivel de peligrosidad', 0.2)
    RETURNING id INTO v_sub1_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Periodo de ocupación', 'Periodos del día de ocupación', 0.3)
    RETURNING id INTO v_sub2_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Densidad de usuarios', 'Nivel de ocupación respecto a dimensiones', 0.1)
    RETURNING id INTO v_sub3_id;

	INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso)
	VALUES (v_indicador_id, 'Sitios e inmuebles adyacentes', 'Evaluación del riesgo por inmuebles y espacios adyacentes', 0.4)
	RETURNING id INTO v_sub4_id;
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub1_id, 'Inmueble escasamente peligroso', 1, 'Inmueble con bajo nivel de peligrosidad'),
    (v_sub1_id, 'Inmueble medianamente peligroso', 2, 'Inmueble con peligrosidad media'),
    (v_sub1_id, 'Inmueble altamente peligroso', 3, 'Inmueble con alto nivel de peligrosidad'),
    (v_sub1_id, 'Inmueble sin uso o abandonado', 4, 'Inmueble sin uso o en estado de abandono');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub2_id, 'Durante el día y noche', 1, 'Ocupación durante todo el día'),
    (v_sub2_id, 'Durante la noche', 2, 'Ocupación principalmente durante la noche'),
    (v_sub2_id, 'Durante el día', 3, 'Ocupación principalmente durante el día'),
    (v_sub2_id, 'Ocupación informal o deshabitado', 4, 'Ocupación informal o inmueble deshabitado');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_sub3_id, 'Ocupación baja', 1, 'Ocupación baja respecto a dimensiones de inmueble'),
    (v_sub3_id, 'Medianamente ocupado', 2, 'Medianamente ocupado respecto a dimensiones de inmueble'),
    (v_sub3_id, 'Altamente ocupado', 3, 'Altamente ocupado respecto a dimensiones de inmueble'),
    (v_sub3_id, 'Ocupación informal o deshabitado', 4, 'Ocupación informal o deshabitado');

	INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
	(v_sub4_id, 'Adyacente a inmueble escasamente peligroso', 1, 'Adyacente a inmueble escasamente peligroso o a espacio público limpio'),
    (v_sub4_id, 'Adyacente a inmueble medianamente peligroso', 2, 'Adyacente a inmueble medianamente peligroso'),
    (v_sub4_id, 'Adyacente a inmueble altamente peligroso', 3, 'Adyacente a inmueble altamente peligroso'),
    (v_sub4_id, 'Adyacente a inmueble abandonado', 4, 'Adyacente a inmueble abandonado, sitio eriazo o espacio público con acumulación de basura');
    
    RAISE NOTICE 'Indicador "Uso y ocupación" creado con ID: %', v_indicador_id;
END $$;

DO $$
DECLARE
    v_amenaza_id INTEGER;
    v_indicador_id INTEGER;
    v_muro_cortafuego_id INTEGER;
    v_deteccion_alarma_id INTEGER;
    v_extincion_id INTEGER;
    v_distancia_grifos_id INTEGER;
    v_equipamiento_bomberos_id INTEGER;
    v_ancho_calle_id INTEGER;
    v_numero_calles_id INTEGER;
	v_dificultad_acceso_id INTEGER;
BEGIN
    SELECT id INTO v_amenaza_id FROM Amenazas WHERE nombre = 'Incendio';
    
    INSERT INTO Indicadores (amenaza_id, nombre, descripcion, peso) 
    VALUES (v_amenaza_id, 'Control del fuego', 'Medidas de control y prevención activa contra incendios', 0.3)
    ON CONFLICT (amenaza_id, nombre) DO NOTHING
    RETURNING id INTO v_indicador_id;
    
    IF v_indicador_id IS NULL THEN
        SELECT id INTO v_indicador_id FROM Indicadores 
        WHERE amenaza_id = v_amenaza_id AND nombre = 'Control del fuego';
    END IF;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Muro cortafuego', 'Existencia de muros cortafuegos', 0.25)
    RETURNING id INTO v_muro_cortafuego_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Sistema de detección y alarma', 'Sistemas de detección temprana de incendios', 0.15)
    RETURNING id INTO v_deteccion_alarma_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Sistema de extinción', 'Sistemas para extinguir incendios', 0.1)
    RETURNING id INTO v_extincion_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Distancia a grifos', 'Distancia a fuentes de agua para bomberos', 0.1)
    RETURNING id INTO v_distancia_grifos_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Equipamiento de bomberos', 'Equipamiento disponible para bomberos', 0.1)
    RETURNING id INTO v_equipamiento_bomberos_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Ancho de calle', 'Ancho de las calles de acceso', 0.1)
    RETURNING id INTO v_ancho_calle_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Número de calles de acceso', 'Cantidad de vías de acceso', 0.1)
    RETURNING id INTO v_numero_calles_id;

	INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Dificultad de acceso', 'Facilidad de acceso para equipos de emergencia', 0.1)
    RETURNING id INTO v_dificultad_acceso_id;
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_muro_cortafuego_id, 'Con muro cortafuego', 1, 'Todos los lados poseen muro cortafuego o es una edificación aislada o separada'),
    (v_muro_cortafuego_id, 'Sin muro cortafuego', 4, 'No posee muro cortafuego');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_deteccion_alarma_id, 'Sistema automático de alarma', 1, 'Posee sistema automático de alarma'),
    (v_deteccion_alarma_id, 'Sistema manual de alarma', 2, 'Posee sistema manual de alarma'),
    (v_deteccion_alarma_id, 'Detección por terceros', 3, 'Detección por terceros'),
    (v_deteccion_alarma_id, 'Sin detección', 4, 'Sin detección');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_extincion_id, 'Sistema fijo y extintor', 1, 'Posee sistema fijo de extinción y extintor'),
    (v_extincion_id, 'Sistema fijo de extinción', 2, 'Posee sistema fijo de extinción'),
    (v_extincion_id, 'Extintor', 3, 'Posee extintor'),
    (v_extincion_id, 'Sin sistema de extinción', 4, 'No posee sistema de extinción');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_distancia_grifos_id, '≤ 50m', 1, 'Distancia ≤ 50m'),
    (v_distancia_grifos_id, '50-100m', 2, '50m > distancia ≤ 100m'),
    (v_distancia_grifos_id, '100-150m', 3, '100m > distancia ≤ 150m'),
    (v_distancia_grifos_id, '> 150m', 4, 'Distancia > 150m');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_equipamiento_bomberos_id, 'Con equipamiento eficiente', 1, 'Bomberos cuenta con equipamiento tecnológico eficiente'),
    (v_equipamiento_bomberos_id, 'Sin equipamiento eficiente', 4, 'Bomberos no cuenta con equipamiento tecnológico eficiente');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_ancho_calle_id, '> 7m', 1, 'acceso > 7 m'),
    (v_ancho_calle_id, '5-7m', 2, '5 m ≤ acceso ≤ 7 m'),
    (v_ancho_calle_id, '3-5m', 3, '3 m ≤ acceso < 5 m'),
    (v_ancho_calle_id, '≤ 3m', 4, 'acceso ≤ 3 m');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_numero_calles_id, '4 calles', 1, '4 calles de acceso'),
    (v_numero_calles_id, '3 calles', 2, '3 calles de acceso'),
    (v_numero_calles_id, '2 calles', 3, '2 calles de acceso'),
    (v_numero_calles_id, '1 calle', 4, '1 calle de acceso');

	INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_dificultad_acceso_id, 'Edificio de esquina o manzana', 1, 'Edificio de esquina o edificio manzana'),
    (v_dificultad_acceso_id, 'Acceso adecuado por una vía', 2, 'Acceso adecuado por una vía'),
    (v_dificultad_acceso_id, 'Acceso dificultado por mobiliario', 3, 'Acceso dificultado por mobiliario'),
    (v_dificultad_acceso_id, 'Sin acceso vehicular', 4, 'Sin acceso vehicular');
    
    RAISE NOTICE 'Indicador "Control del fuego" creado con ID: %', v_indicador_id;
END $$;

DO $$
DECLARE
    v_amenaza_id INTEGER;
    v_indicador_id INTEGER;
    v_plan_gestion_id INTEGER;
    v_inspeccion_id INTEGER;
    v_plan_simulacros_id INTEGER;
BEGIN
    SELECT id INTO v_amenaza_id FROM Amenazas WHERE nombre = 'Incendio';
    
    INSERT INTO Indicadores (amenaza_id, nombre, descripcion, peso) 
    VALUES (v_amenaza_id, 'Gestión del fuego', 'Medidas de gestión y administración contra incendios', 0.2)
    ON CONFLICT (amenaza_id, nombre) DO NOTHING
    RETURNING id INTO v_indicador_id;
    
    IF v_indicador_id IS NULL THEN
        SELECT id INTO v_indicador_id FROM Indicadores 
        WHERE amenaza_id = v_amenaza_id AND nombre = 'Gestión del fuego';
    END IF;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Plan de gestión de incendios', 'Existencia de planes de gestión', 0.4)
    RETURNING id INTO v_plan_gestion_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Inspección de seguridad', 'Inspecciones periódicas de seguridad', 0.4)
    RETURNING id INTO v_inspeccion_id;
    
    INSERT INTO Sub_indicadores (indicador_id, nombre, descripcion, peso) 
    VALUES (v_indicador_id, 'Planes de emergencia y simulacros', 'Capacitación y simulacros', 0.2)
    RETURNING id INTO v_plan_simulacros_id;
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_plan_gestion_id, 'Con plan de gestión', 1, 'Existe un plan de gestión de incendios asociado al Sitio'),
    (v_plan_gestion_id, 'Sin plan de gestión', 4, 'No existe un plan de gestión de incendios asociado al Sitio');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_inspeccion_id, 'Inspección periódica', 1, 'Existe institución de inspección y ejecuta registros periódicos'),
    (v_inspeccion_id, 'Inspección sin fiscalizar', 3, 'Existe institución de inspección, pero no fiscaliza'),
    (v_inspeccion_id, 'Sin inspección', 4, 'No existe institución de inspección de seguridad contra incendios');
    
    INSERT INTO Clases (sub_indicador_id, nombre, valor, descripcion) VALUES
    (v_plan_simulacros_id, 'Con capacitación', 1, 'Existe capacitación de seguridad contra incendios'),
    (v_plan_simulacros_id, 'Sin entrenamiento', 4, 'No hay entrenamiento de seguridad contra incendios');
    
    RAISE NOTICE 'Indicador "Gestión del fuego" creado con ID: %', v_indicador_id;
END $$;

COMMIT;
