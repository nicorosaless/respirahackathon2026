# Los datos del reto: qué hay y qué no

Reconocimiento hecho el 1 de octubre de 2026 sobre MareNostrum. Este documento
solo lleva estructura, recuentos y agregados. No contiene datos de ningún
sujeto.

Se regenera con tres scripts:

```bash
python3 scripts/explore_clinical.py <tabla.csv>
python3 scripts/inventory.py <carpeta> --out outputs/inventario.csv
python3 scripts/explore_inventory.py outputs/inventario.csv
```

## Dónde están

```
<datos del reto>/EPOC-challenge/
    EARLY_Hackathon_anonymous_definitive.csv     tabla clínica, 86 filas y 43 columnas
    1.zip ... 86.zip                             un zip por sujeto, 32 GB en total
```

El nombre del zip es el `random_id` de la tabla. Dentro de cada zip hay un
estudio DICOM con varias series: `<id>/ST000000/SE00000N/CT00000N`. Los ficheros
no llevan extensión.

Es la cohorte EARLY COPD. Todos son fumadores o exfumadores de 35 a 50 años.

## La tabla clínica

86 sujetos. 30 son casos (`caso_v1 = 1`) y 56 controles. `caso_v1` coincide
exactamente con tener FEV1/FVC posbroncodilatador por debajo de 0,7 en la
visita 1.

Tiene tres bloques.

**Visita 1 (`_v1`), completa para los 86.**

| Columnas | Qué son |
|---|---|
| `edat_round_v1`, `sexo_num_v1`, `altura_v1`, `peso_v1`, `imc_v1` | Edad, sexo, talla, peso e IMC. Sexo 1 es hombre y 2 es mujer, según el codebook |
| `fumador_exfumador_num_v1`, `actual_fuma_num_v1`, `paquetes_año_v1` | Tabaco. Todos son fumadores o exfumadores. 61 fuman en la visita 1 |
| `asma_num_v1` | Antecedente de asma, 7 sujetos |
| `FVC...`, `FEV1...` antes y después del broncodilatador, en litros | Espirometría |
| `FEV1pp_GLI_v1`, `FVCpp_GLI_v1` y sus `pre` | Porcentaje del predicho con las ecuaciones GLI |
| `DLCO_v1` | DLCO en porcentaje del predicho. Mediana 75 |
| `mmrc_num_v1`, `CAT_v1`, `COPD_PS_v1` | Cuestionarios de síntomas |
| `FENO_v1` | Óxido nítrico espirado. Es la única variable biológica de la tabla |

**TC (`enfisema_SI_v1`).** Enfisema visual, sí o no. 23 sujetos lo tienen, 61
no, y falta en 2. Lo tienen 15 de los 30 casos y 8 de los 54 controles
valorados. Es la única variable de la tabla que sale de la imagen.

**Visita 2 (`_v2`), para 76 de los 86.** Mediana de 3,6 años después, con un
rango de 2,9 a 9,6. Repite espirometría, DLCO, cuestionarios, FENO, peso, talla
y tabaco.

### Trampas de la tabla

- **Coma decimal.** Los números vienen como `"3,52"`. `maps.tables.read_table`
  los convierte.
- **`DLCO_v2` no está en las mismas unidades que `DLCO_v1`.** La de la visita 1
  es porcentaje del predicho (25 a 107). La de la visita 2 va de 3 a 37, que
  parece el valor absoluto. No se pueden restar. El codebook dice "DLCO %" para
  las dos, así que es un error de los datos o del codebook.
- **`mmrc_num_v2` va de 1 a 4 y `mmrc_num_v1` de 0 a 3.** Parece la misma
  escala desplazada una unidad.
- **`COPD_PS_v2` va de 6 a 14 y `COPD_PS_v1` de 1 a 11.** Tampoco son
  comparables tal cual.
- **No hay columna que marque entrenamiento y validación.**
- **No hay ómicas ni biomarcadores en sangre.** Solo FENO.

Las tres primeras hay que confirmarlas con las expertas antes de usar la
visita 2.

### Lo que se deduce de la tabla

- **Cambio de grupo.** De los 77 con espirometría en las dos visitas, 2
  controles pasan a tener obstrucción y 4 casos dejan de tenerla.
- **Caída del FEV1.** Mediana de 5 mL al año, con un rango de -218 a 221. Con
  3,6 años de seguimiento el ruido de la espirometría pesa más que la caída
  real.
- **Controles con algún criterio de pre-EPOC.** De 56 controles: 8 tienen
  enfisema visual, 34 tienen DLCO por debajo del 80 %, 18 tienen CAT de 10 o
  más y 6 tienen mMRC de 2 o más. Solo 13 no cumplen ninguno.
- **Controles con enfisema.** Tienen más síntomas (CAT mediano de 14 frente a
  4,5), menos DLCO (71,5 frente a 77,5) y peor FEV1 (89 % frente a 99 %).
- **DLCO y lo demás.** Correlación de Spearman de 0,38 con el FEV1, de -0,37
  con el enfisema visual y de -0,26 con el CAT.

### Lo que dice el codebook

Los organizadores dieron un codebook (`epoc-codebook.xlsx`) con el nombre, la
descripción y la escala de cada columna. Confirma tres cosas y deja el resto
sin resolver.

- `caso_v1` se define por FEV1/FVC posbroncodilatador menor de 0,7.
- `sexo_num_v1`: 1 es hombre y 2 es mujer.
- `fumador_exfumador_num_v1`: todos tienen una dosis acumulada de más de 10
  paquetes-año. Es el criterio de entrada en la cohorte.
- De `enfisema_SI_v1` solo dice "emphysema visit 1". No dice quién lo leyó ni
  con qué criterio.
- No explica el cambio de escala de `mmrc_num_v2` ni de `COPD_PS_v2`.
- No menciona ninguna variable de TC aparte del enfisema, ni reparto entre
  entrenamiento y validación, ni datos biológicos más allá de FENO.

## Las TC

805 series DICOM en 86 sujetos. 738 son de TC. Todos los escáneres son de GE.

Cada sujeto trae entre 3 y 38 series: localizadores, capturas de pantalla,
informes de dosis, reconstrucciones coronales y, en algunos, estudios de otras
fechas y de otras partes del cuerpo. La serie útil hay que elegirla.

### La serie que usamos

TC axial original de tórax, sin contraste, de corte fino (1,25 mm o menos), con
kernel STANDARD y de la fecha más antigua. Es la regla por defecto de
`scripts/make_manifest.py`.

- **80 sujetos** tienen una serie así, con kernel STANDARD. En 3 de ellos esa
  serie está incompleta, y el modelo final usa en su lugar la reconstrucción de
  kernel duro de la misma adquisición: 77 con STANDARD y 3 con BONEPLUS.
- **6 sujetos se quedan fuera**: 38, 39, 49, 52, 75 y 80. Solo tienen TC de
  abdomen, cortes de 3 mm, contraste, kernel duro o ninguna serie completa.
- **3 de las 80 tienen la serie incompleta**: 6, 8 y 68. A la reconstrucción
  STANDARD le faltan cortes, lo detecta `scripts/check_series.py` por la
  posición de cada corte. El análisis usa las 77 restantes.
- 79 de las 80 TC basales son de 2015 a 2017. Coinciden con el reclutamiento.
- Casi todos los sujetos tienen además la misma adquisición con kernel duro
  (`BONEPLUS`, descrita como "pulmón").

### Los confusores que sí hay

| Variable | Valores en las 80 TC elegidas |
|---|---|
| Voltaje del tubo (kVp) | 100 en 39, 80 en 24 y 120 en 17 |
| Modelo de escáner | Optima CT660 en 35, LightSpeed VCT en 34, BrightSpeed en 10, Revolution Apex en 1 |
| Protocolo | Baja dosis en 62, alta resolución para enfisema en 12, otros en 6 |
| Grosor de corte | 1,25 mm en 79 y 0,625 mm en 1 |
| Tamaño de píxel | De 0,60 a 0,93 mm, mediana 0,77 |

El kVp y el modelo de escáner tienen que entrar como covariables del modelo
normativo, junto con el tabaquismo activo.

### Lo que no hay

- **TC en espiración.** Solo 3 sujetos tienen inspiración y espiración. No se
  puede medir atrapamiento aéreo en la cohorte.
- **TC de seguimiento para todos.** 17 sujetos tienen TC finas de tórax en más
  de una fecha. Sirven para un análisis longitudinal pequeño.

## Preguntas abiertas

1. Los organizadores hablan de 80 sujetos para entrenar y 15 para validar. En
   la carpeta hay 86 y la tabla no marca ningún reparto. ¿Los 15 de validación
   están aparte? ¿Qué hay que predecir en ellos y con qué métrica?
2. ¿`DLCO_v2`, `mmrc_num_v2` y `COPD_PS_v2` están en otra escala que en la
   visita 1?
3. ¿La TC de cada sujeto se hizo en la visita 1? ¿Qué hacemos con los que
   tienen varias fechas?
4. ¿Hay datos biológicos además de FENO?
