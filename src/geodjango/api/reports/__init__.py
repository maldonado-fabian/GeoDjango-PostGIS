"""Generación del PDF de resumen global de riesgo (amenaza incendio y otras).

Módulos:
- niveles: cortes y colores por nivel (espejo de risk-map/src/utils/colores.ts).
- queries: consultas a PostGIS (reutilizan el SQL de índice de riesgo de views.py).
- charts: gráficos matplotlib (mapas + donas) -> PNG.
- text:   plantillas de texto narrativo con números dinámicos.
- pdf:    ensamblado del PDF con ReportLab Platypus.
"""
