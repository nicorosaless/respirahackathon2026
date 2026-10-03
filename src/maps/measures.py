"""Catálogo de medidas de TC: nombre, unidad, descripción y qué sentido indica más daño.

Vive aparte de `features.py` para que el análisis y la app lo lean sin cargar
las librerías de imagen.
"""

from __future__ import annotations

WHOLE_LUNG = "pulmon"
# Nombre, unidad, descripción y qué sentido indica más daño. La app lo lee tal cual.
MEASURES = {
    "perc15": ("Perc15", "HU", "Percentil 15 de la densidad. Baja cuando se pierde tejido.", "menor"),
    "laa950": ("%LAA-950", "%", "Porcentaje del parénquima (sin vasos ni vías segmentadas) por debajo de -950 HU. Índice clásico de enfisema.", "mayor"),
    "laa910": ("%LAA-910", "%", "Porcentaje del pulmón por debajo de -910 HU.", "mayor"),
    "laa950_smooth": ("%LAA-950 suavizado", "%", "%LAA-950 tras un filtro gaussiano de 1 mm, que reduce el ruido de la imagen.", "mayor"),
    "haa": ("Alta atenuación", "%", "Porcentaje entre -600 y -250 HU. Sube con inflamación o cambios intersticiales.", "mayor"),
    "mld": ("Densidad media", "HU", "Densidad media del pulmón.", "menor"),
    "densidad_g_l": ("Densidad", "g/L", "Masa de tejido por litro de pulmón.", "menor"),
    "masa_g": ("Masa", "g", "Masa de tejido de la región.", "menor"),
    "volumen_ml": ("Volumen", "mL", "Volumen de la región en la TC.", "mayor"),
    "agrupamiento": ("Agrupamiento del enfisema", "", "Entre las parejas de vóxeles vecinos con alguno de baja densidad, cuántas tienen los dos. Sube cuando forman focos.", "mayor"),
    "vasos_bv5_tbv": ("Vasos pequeños", "", "Fracción del volumen vascular que desaparece al quitar lo más fino que un vaso de 5 mm² de sección. Aproximación morfológica a la poda vascular.", "menor"),
    "vasos_por_litro": ("Volumen vascular", "mL/L", "Volumen de vasos por litro de pulmón.", "menor"),
    "arterias_bv5_tbv": ("Arterias pequeñas", "", "La misma aproximación morfológica, solo con las arterias.", "menor"),
    "via_ramas": ("Ramas de vía aérea", "", "Número de ramas del árbol bronquial visibles en la TC.", "menor"),
    "via_ramas_por_litro": ("Ramas por litro", "1/L", "Ramas de vía aérea por litro de pulmón.", "menor"),
    "via_longitud_mm": ("Longitud de vía aérea", "mm", "Suma de la longitud de todas las ramas del árbol bronquial que se llegan a segmentar.", "menor"),
    "via_longitud_conectada_mm": ("Longitud de vía aérea conectada", "mm", "Lo mismo, contando solo lo que está unido a la tráquea.", "menor"),
    "via_longitud_fina_mm": ("Longitud de vía aérea fina", "mm", "Longitud de las vías de menos de 3 mm de diámetro de luz: las más periféricas que se segmentan.", "menor"),
    "via_longitud_gruesa_mm": ("Longitud de vía aérea gruesa", "mm", "Longitud de las vías de 3 mm o más de diámetro de luz.", "menor"),
    "via_fraccion_fina": ("Fracción de vía aérea fina", "", "Parte de la longitud del árbol que corresponde a vías de menos de 3 mm de luz.", "menor"),
    "via_extremos": ("Extremos del árbol", "", "Número de extremos libres del árbol bronquial unido a la tráquea.", "menor"),
    "via_longitud_lobar_mm": ("Longitud de vía aérea en el lóbulo", "mm", "Longitud del árbol bronquial dentro del lóbulo. En el pulmón entero, la suma de los cinco.", "menor"),
    "via_calibre_central_mm": ("Calibre central", "mm", "Media geométrica del diámetro de la luz en las 15 vías más anchas: tráquea, bronquios principales, lobares y primeros segmentarios.", "menor"),
    "via_disanapsia": ("Disanapsia, aproximada", "", "Calibre de las 15 vías más anchas partido por la raíz cúbica del volumen pulmonar. Baja cuando la vía aérea es pequeña para su pulmón. No son las 19 localizaciones anatómicas de Smith 2020.", "menor"),
    "via_grosor_pared_mm": ("Grosor de pared, estimado", "mm", "Grosor medio de la máscara de pared en las vías de 6 a 20 mm de perímetro interno. Sale de la segmentación, no del perfil de densidad del bronquio.", "mayor"),
    "via_pared_pct": ("Área de pared, aproximada", "%", "Parte del área del bronquio que ocupa la pared, en las mismas vías, suponiendo secciones circulares.", "mayor"),
    "via_pi10_mm": ("Pi10, aproximado", "mm", "Raíz del área de pared de una vía teórica de 10 mm de perímetro interno, a partir de la máscara de pared y secciones circulares.", "mayor"),
}

# Los porcentajes de baja atenuación se comparan en logaritmo: en un pulmón joven están pegados a
# cero y lo que distingue a dos sujetos es cuántas veces se multiplica, no cuántos puntos sube.
# Antes del logaritmo se suma una constante, en puntos porcentuales, para que el cero tenga valor.
# No es un límite de detección medido: `scripts/check_score.py` comprueba que el resultado no depende de ella.
LOG_MEASURES = ("laa950", "laa910", "laa950_smooth")
LOG_FLOOR = 0.01


def measures_dictionary() -> dict[str, dict[str, str]]:
    return {key: {"nombre": name, "unidad": unit, "descripcion": text, "peor": worse}
            for key, (name, unit, text, worse) in MEASURES.items()}
