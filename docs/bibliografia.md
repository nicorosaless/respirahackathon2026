# Bibliografía: por qué cada elección

Las referencias que respaldan cada pieza del modelo, con lo que mostró cada una
y una frase para decir en voz alta. Se reunió el 1 de
octubre de 2026 y no la ha revisado nadie con formación clínica.

**Cómo leerla.** [V] significa que abrí el resumen o el texto (casi siempre vía Europa PMC o la web de la revista) y la cifra citada sale de ahí. [NV] significa que no pude abrirlo. Las citas completas con DOI están al final.

## 1. TotalSegmentator y nnU-Net

- **Wasserthal 2023 [V].** Se entrenó con 1204 TC para 104 estructuras (incluye lóbulos pulmonares). Obtuvo Dice 0,943 en test, frente a 0,932 contra 0,871 de otro modelo público (p<0,001).
- **Isensee 2021 [V].** nnU-Net se configura solo y supera a la mayoría de métodos en 23 conjuntos públicos de competición.
- **Tarea `lung_vessels` [V, README oficial de GitHub].** Da arterias, venas, vía aérea y pared de vía aérea. Cita "en parte" el dataset de Liu 2025. Ese dataset (AirRC, 254 TC) reporta Dice 0,953 venas, 0,950 arterias, 0,941 luz y 0,866 pared [V]. Son cifras del modelo de los autores del dataset, no una validación independiente de TotalSegmentator. La versión anterior (Task 258) se entrenó con 248 sujetos [V, Zenodo].
- **Qué falta.** No encontré ninguna validación independiente de los lóbulos ni de las vías aéreas o vasos de TotalSegmentator en EPOC o enfisema. Un trabajo de 2025 (Arrigoni, Radiol Med) dice que TotalSegmentator "struggles with severely altered images", pero solo lo compara visualmente [V].

**Frase:** "Usamos TotalSegmentator por su validación general en 1204 TC y porque es reproducible; la segmentación de vía aérea y vasos en pulmón enfermo no está validada de forma independiente, y por eso la revisamos visualmente."

## 2. %LAA-950 y Perc15

- **Gevenois 1996 [V].** Se comparó la TC con la morfometría microscópica en 38 sujetos con TC preoperatoria. Con umbrales de −900 a −970 HU, la correlación más fuerte fue la de −950 HU. Los autores concluyen que es un índice válido de enfisema.
- **Lynch 2015 [V].** Declaración de la Fleischner Society sobre subtipos de EPOC definibles por TC. Define el enfisema centrilobulillar (traza, leve, moderado, confluente, destructivo avanzado), el panlobulillar y el paraseptal, y trata la TC cuantitativa como complemento de la lectura visual.
- **San José Estépar 2025, AJRCCM [V].** Es la declaración de posición de la Fleischner Society sobre densitometría por TC en ensayos clínicos. Sí existe. Dice que la TC está validada frente a patología. Da un ICC test-retest de 0,99 con técnica adecuada y asocia un LAA-950 >5 % con más exacerbaciones y mortalidad. Pide CTDIvol ≤3 mGy, corte ≤1 mm y kernel estandarizado, y recomienda excluir o estratificar a los fumadores actuales.
- **QIBA [V].** El perfil de densitometría pulmonar solo da claims longitudinales. Sin ajuste de volumen, el cambio mínimo detectable es ≥3,7 % para RA-950 y ≥18 HU para Perc15. Con ajuste de volumen, ≥11 HU. Afirma explícitamente que "there is not sufficient data" para un claim transversal.

**Frase:** "El umbral de −950 HU se validó contra histología y la Fleischner 2025 lo respalda, pero ningún estándar da todavía un valor transversal comparable entre escáneres, por eso normalizamos."

## 3. Kernel, dosis y reducción de ruido

- **Boedeker 2004 [V].** Con 42 sujetos, los kernels que sobrerrealzan desplazan el índice de enfisema 9,4 puntos (de 35,5 % a 44,9 %). Los kernels nítidos lo desplazan 2,4 y los suaves −1,0.
- **Gierada 2010 [V].** Con 21 sujetos y 20 combinaciones de grosor y kernel, el efecto es máximo en valores intermedios (10–30 %) y menor en los extremos. Esto puede explicar parte de la discrepancia entre ICC y diferencia absoluta en cohortes con poco enfisema.
- **Schilham 2006 [V].** El %LAA depende mucho del ruido, porque usa un único umbral. Tras un filtro ponderado por ruido (NOVA), las puntuaciones de dosis alta y baja coinciden dentro de 2–3 puntos.
- **den Harder 2018 [V].** Con 22 pacientes y reducciones de dosis del 45, 60 y 75 %, la dosis baja sobreestima el enfisema con FBP y la reconstrucción iterativa lo subestima.
- **Gallardo-Estrella 2016 [V].** Con 369 sujetos de COPDGene, normalizar el kernel redujo la diferencia entre kernels de 7,7±2,7 a 0,3±0,7 puntos y de 7,2±3,8 a −0,1±0,5 en los dos escáneres.
- **Bak 2020 [V].** En 131 participantes, la conversión de kernel con deep learning redujo la variación del kernel nítido de la TC de baja dosis.
- **de Boer 2019 [V].** El filtrado de ruido posterior a la reconstrucción cambia el %LAA-950 de forma significativa y mejora su correlación con la función pulmonar.
- **Sotoudeh-Paima 2026 [V, solo resumen].** Muestra que LAA-950 es poco robusto entre condiciones de imagen.
- **Sus propios números.** Ningún trabajo da un ICC de 0,16 a 0,95 con un filtro gaussiano. Es un resultado propio y debe presentarse como tal.

**Frase:** "La literatura muestra desde 2004 que kernel y ruido mueven el %LAA-950 varios puntos, y nuestros datos lo reproducen: ICC 0,16 en bruto y 0,95 tras un filtro suave."

## 4. Fumar actual sube la densidad

- **Ashraf 2011 [V].** Con 726 fumadores de un cribado de cáncer, el PD15 ajustado por volumen fue 55 g/l en fumadores actuales y 45 g/l en exfumadores (diferencia de 10 g/l). Tras dejar de fumar (n=77) cayó 6,2 g/l el primer año y 3,6 g/l el segundo. Tras una recaída (n=18) subió 3,7 g/l. El g/l equivale aproximadamente al HU, pero la unidad no es la misma.
- **Zach 2016 [V].** En COPDGene (n=6762), el %LAA-950 fue 4,2±7,1 en actuales y 7,7±9,7 en exfumadores. Tras ajustar, los actuales tienen 3,5 puntos menos de %LAA-950 inspiratorio y 6,0 menos de %LAA-856 espiratorio. Con normalización por cuantiles la diferencia pierde significación (0,27 puntos, p=0,13).
- **Fleischner 2025 [V].** Atribuye el efecto a inflamación que enmascara el enfisema y recomienda excluir o estratificar.
- **Sus datos.** Perc15 de −890 frente a −912 HU (22 HU) es mayor que el efecto publicado de unos 10 g/l. Sus fumadores son jóvenes y la cohorte no es comparable, así que dígalo.

**Frase:** "Los fumadores actuales tienen el pulmón más denso por inflamación: unos 10 g/l en Ashraf y 3,5 puntos de %LAA-950 en COPDGene, así que corregimos por tabaquismo actual."

## 5. Ajuste por volumen

- **Stoel 2004 [V, solo resumen].** Revisa la estandarización de la densitometría (adquisición, parámetro, procesado).
- **Parr 2008 [V].** Con 71 pacientes con déficit de alfa-1 antitripsina seguidos 2 años, "casi la mitad" de la pérdida de densidad se debió a hiperinsuflación aparente. Concluye que Perc15 en la región media es la medida más robusta.
- **Ashraf 2011 [V].** Usó PD15 ajustado a la TLC predicha.
- **QIBA y Fleischner 2025 [V].** Con ajuste de volumen el cambio mínimo detectable baja de 18 a 11 HU. El modelo de esponja conserva la masa pulmonar.
- **Matiz.** Estos estudios son longitudinales. Para comparación transversal entre personas, el ajuste es razonable pero está menos probado.

**Frase:** "Ajustamos por volumen porque casi la mitad de la 'pérdida' de densidad puede ser solo cuánto aire inspiró la persona (Parr 2008)."

## 6. Recuento total de vías aéreas y medidas de vía aérea sin obstrucción

- **Kirby 2018 [V].** En CanCOLD, el recuento total estaba un 19 % más bajo en EPOC GOLD I-II que en nunca fumadores, y un 17 % más bajo que en fumadores de riesgo, ajustando por enfisema. Se asoció con la caída de FEV1 (p=0,02) y de FEV1/FVC (p=0,01).
- **Kirby 2021 [V].** Se estudiaron 316 fumadores de riesgo y 56 (18 %) desarrollaron EPOC en 3,1 años. Solo el recuento se asoció con EPOC incidente, con un OR de aproximadamente 2 por 1 DE de descenso. El LAA-856, Pi10 y el área de pared no fueron significativos.
- **Oelsner 2018 [V].** En MESA Lung (n=1830, sin enfermedad respiratoria), Pi10 más alto se asoció con una caída de FEV1 un 9 % más rápida y con EPOC incidente (OR 2,22 por DE), ajustando por enfisema.
- **Advertencia.** El recuento depende de la segmentación (VIDA en Kirby). No hay validación del recuento con TotalSegmentator.

**Frase:** "Menos vías aéreas visibles predice EPOC en fumadores sin obstrucción (OR ≈2 por desviación estándar, CanCOLD), incluso con el enfisema ajustado."

## 7. Disanapsis

- **Smith 2020, JAMA [V].** En MESA Lung (n=2531), el cuartil más bajo de la razón vía aérea/pulmón tuvo 9,8 casos de EPOC por 1000 personas-año, frente a 1,2 en el cuartil más alto (RR 8,12). En CanCOLD (n=1272) fueron 80,6 frente a 24,2 (RR 3,33). En SPIROMICS (n=2726) la caída de FEV1 varió por cuartil. La razón es el diámetro medio de luz en 19 localizaciones dividido por la raíz cúbica del volumen pulmonar.

**Frase:** "Quien tiene la vía aérea estrecha para su pulmón tiene un riesgo de EPOC varias veces mayor, y esa razón se mide en una TC." Smith midió adultos: que esa desproporción venga de nacimiento es una hipótesis, y los propios autores admiten que el remodelado y la hiperinsuflación pueden contribuir. Nuestra disanapsia es una aproximación: 15 vías más anchas, no las 19 localizaciones.

## 8. Poda vascular

- **Estépar 2013 [V].** En fumadores, el %LAA-950 se relaciona inversamente con las razones de vasos pequeños (<5 mm²). Esas razones se asocian con saturación, DLCO y capacidad de ejercicio.
- **Washko 2019 [V].** En 3506 TC de COPDGene, 10 ml menos de BV5 arterial se asocian con 1 ml más de volumen del ventrículo derecho. En personas con poda, el volumen del ventrículo derecho se asocia con mayor mortalidad.
- **Pistenmaa 2021 [V].** En 4227 participantes de COPDGene, más poda arterial se asoció con progresión del enfisema (0,11 puntos/año por DE) y con caída de FEV1/FVC.
- **Contrapunto, Synn 2019 [V].** En Framingham (n=2410, población general), los fumadores tenían más volumen vascular (+4,6 ml total, +2,1 ml de vasos pequeños), no menos. Los autores sugieren que la "poda" radiológica no refleja la patología.
- **Uso en sujetos sanos.** No tengo un estudio que muestre poda en fumadores con espirometría normal.

**Frase:** "La poda vascular distal acompaña y precede al enfisema en cohortes de EPOC, pero en población general no se ve, así que la presentamos como hipótesis."

## 9. Agrupamiento espacial de las zonas de baja atenuación

- **Mishima 1999 [V].** El tamaño de los clusters de LAA sigue una ley de potencias con exponente D. Los pacientes con EPOC y LAA% normal tenían D significativamente menor que los sanos, y D solo correlacionó con DLCO. Los autores lo proponen como marcador de enfisema precoz.
- **Virdee 2021 [V].** En CanCOLD (n=1294), el join count normalizado fue el único que separó EPOC leve de moderada-grave (1,98±3,61 frente a 1,44±2,14 %). Fue la medida con mayor contribución a DLCO/VA y a la puntuación visual.
- **Vestal 2023 [V].** En 587 sujetos de COPDGene, el tamaño medio de cluster de un modelo de proceso puntual se asoció mucho más con los desenlaces clínicos que el %LAA y la puntuación visual.
- **Advertencia.** El ruido crea clusters falsos. Aplique el mismo suavizado antes de agrupar y dígalo.

**Frase:** "Dos personas con el mismo %LAA pueden tener patrones distintos, y la agrupación espacial captura esa diferencia, más relacionada con la DLCO."

## 10. Modelado normativo

- **GLI 2012, Quanjer [V].** Ecuaciones espirométricas con método LMS para 3–95 años, a partir de 97.759 registros de no fumadores sanos de 72 centros y 33 países. Incluye límites inferiores de normalidad según la edad.
- **Hoffman 2014, MESA Lung [V].** En 854 nunca fumadores sanos, la mediana de enfisema fue 1,1 % (RIC 0,5–2,5 %). Es 1,2 puntos mayor en hombres, y sube con la edad y la talla. Hay ecuaciones de referencia para nunca, ex y fumadores actuales. Los participantes tienen 54–93 años y los autores dicen que la validación está pendiente. No sirve directamente para 35–50 años.
- **Stoel 2019 [V].** Es un precedente de puntuación z de masa pulmonar frente a 76 controles sanos, usada en déficit de alfa-1 antitripsina.
- **Método, Marquand 2016 [V] y Bethlehem 2022 [V].** Marquand introduce los modelos normativos para describir cada individuo como desviación, sin dicotomizar. Bethlehem hace gráficas de crecimiento cerebral con 123.984 RM y 101.457 participantes.
- **Lo que falta.** No encontré ecuaciones de referencia de densidad por TC para adultos jóvenes ni por kernel o escáner.

**Frase:** "Hacemos con la TC lo que GLI hace con la espirometría: puntuamos a cada persona frente a lo esperable, pero nuestra referencia es propia porque no existe una válida para 35–50 años."

## 11. Pre-EPOC y PRISm

- **GOLD 2023 [V, PDF del informe].** Cito textualmente: "Some individuals can have respiratory symptoms and/or structural lung lesions (e.g., emphysema) and/or physiological abnormalities (including low-normal FEV1, gas trapping, hyperinflation, reduced lung diffusing capacity and/or rapid FEV1 decline) without airflow obstruction (FEV1/FVC ≥ 0.7 post-bronchodilation). These subjects are labelled 'Pre-COPD'." PRISm es FEV1/FVC ≥0,7 post-broncodilatador con FEV1 <80 % del valor de referencia.
- **Han 2021 [V].** La propuesta es: "1) respiratory symptoms…; 2) physiologic abnormalities, including low-normal FEV1, DLCO, and/or accelerated FEV1 decline; and/or 3) radiographic abnormalities, including airway abnormalities and emphysema". Ni Han ni GOLD dan umbrales numéricos para DLCO ni para el enfisema. Han admite que "a tighter definition is desirable".
- **Harvey 2015 [V].** Se estudiaron 105 fumadores activos con espirometría normal. Desarrollaron EPOC con obstrucción el 22 % (10/46) de los de DLCO baja (<80 %) y el 3 % (2/59) de los de DLCO normal.
- **McAllister 2014 [V].** En 521 fumadores ≥60 años de un cribado, el enfisema predijo obstrucción incidente (HR 5,14; IC 95 % 2,19–21,1).
- **Wan 2018 [V].** En COPDGene, el PRISm es transicional: entre el 12,4 y el 12,5 % en cada fase, con transiciones frecuentes y mayor mortalidad.
- **Bhatt 2025, JAMA [V parcial].** El esquema multidimensional añade criterios de TC (enfisema, engrosamiento de pared bronquial). El resumen de prensa dice que reclasifica al 15,4 % de los participantes de COPDGene sin obstrucción [NV, fuente secundaria]. Las listas de criterios menores difieren entre fuentes, así que no las cite.

**Frase:** "Pre-EPOC es síntomas, enfisema o DLCO baja sin obstrucción; GOLD no da umbrales, y en fumadores con DLCO baja la obstrucción llegó al 22 % frente al 3 %."

## 12. Por qué no deep learning de extremo a extremo con ~80 sujetos

- **González 2018 [V].** La CNN se entrenó con 7983 participantes de COPDGene. Con ese tamaño dio C 0,856 para detectar EPOC y estadificó bien al 51,1 % en COPDGene y al 29,4 % en ECLIPSE.
- **Balki 2019 [V].** Revisión sistemática de 167 artículos que encuentra pocas metodologías de cálculo de tamaño muestral para ML en imagen médica.
- **Riley 2020 [NV, contenido].** Existe y propone un cálculo de tamaño mínimo contra sobreajuste.
- **Wang 2023 [V].** Con 3821 sujetos de entrenamiento en GOLD 0-2, predecir la caída rápida de FEV1 en GOLD 0 dio un AUC de solo 0,62±0,081 en validación externa. Lo logró con regresión logística sobre biomarcadores TC.
- **Dorosti 2025 [V].** Entrenó con 7194 cortes de solo 78 sujetos y dio AUC 0,80–0,86. Es un ejemplo de por qué conviene evaluar por sujeto, no por corte.
- **Sarsembayeva 2026 [V, solo resumen].** Combina embeddings ResNet con %LAA, Perc15 y volumen. Reporta AUC 0,996 en baja dosis, pero probablemente frente a una etiqueta derivada de la propia TC.
- **Sin referencia sólida.** No encontré un estudio que muestre que las características profundas no superan a la TC cuantitativa en espirometría normal. Lo único defendible es la ausencia de evidencia de que sí la superen con n pequeño.

**Frase:** "Los modelos de extremo a extremo que funcionan usan miles de sujetos (7983 en González); con unos 80 sería sobreajuste, y por eso usamos variables medibles e interpretables."

## 13. Fusión tardía frente a conjunta

- **Stahlschmidt 2022 [V].** Los autores encuentran que las fusiones profundas suelen superar a las unimodales y superficiales. Dicen que "overfitting… is a major challenge" y que las muestras biomédicas suelen ser pequeñas respecto a la dimensionalidad. Citan casos con solo 96 pacientes, proponen transferencia de aprendizaje como remedio y señalan que la fusión tardía no aprende interacciones entre modalidades.
- **Huang 2020 [V, solo resumen].** Revisión de 17 estudios con guías de implementación.
- **Mohsen 2022 [V].** Scoping review de 34 estudios: la fusión temprana fue la más usada (22 de 34) y los modelos multimodales superaron a los unimodales.
- **Qué falta.** Ninguna de estas revisiones recomienda de forma explícita la fusión tardía para muestras pequeñas. Ese argumento es de buena práctica estadística, no un hallazgo establecido. Una frase que vi en búsquedas, que la fusión tardía mejora con baja razón muestra/dimensión, no pude rastrearla a su fuente [NV].

**Frase:** "Fusionamos al final porque con pocos sujetos cada modelo por separado sobreajusta menos; es una decisión prudente, no una ley demostrada, y renunciamos a las interacciones entre modalidades."

## 14. Validación con muestras pequeñas

- **Varma 2006 [V].** En datos nulos simulados, el CV usado también para ajustar hiperparámetros dio errores falsamente bajos: <30 % en el 18,5 % de los datasets con centroides y en el 38 % con SVM. El CV anidado reduce el sesgo de forma considerable.
- **Vabalas 2019 [V].** Con muestras pequeñas, el K-fold produce estimaciones sesgadas, mientras el CV anidado y la partición entrenamiento/test son robustos. Seleccionar variables con todos los datos aporta bastante más sesgo que ajustar parámetros.
- **Ojala y Garriga 2010 [V].** Tests de permutación para saber si el clasificador encontró estructura real.
- **Varoquaux 2018 [V].** Con 100 muestras las barras de error del CV son de aproximadamente ±10 %, y el error estándar entre folds las subestima mucho.

**Frase:** "Con unos 80 sujetos usamos CV anidado, test de permutación e intervalos amplios, porque el error de una validación cruzada simple puede ser de ±10 puntos."

## 15. Cohorte EARLY COPD (Cosío 2020) [V, texto completo en Europa PMC]

- **Diseño.** Prospectivo, multicéntrico, casos y controles 1:2 (NCT02352220), aprobado por los comités éticos de todos los centros. Participaron 12 hospitales terciarios de España y sus centros de atención primaria, con reclutamiento por anuncio local.
- **Inclusión.** "All participants were 35–50 years of age, of Caucasian origin and were current or former smokers (>10 pack-years)". Los casos: "airflow limitation after bronchodilation (FEV1/FVC<0.7)". Los controles: espirometría normal y sin asma previa confirmada.
- **Exclusión.** Déficit de alfa-1 antitripsina, enfermedades que limiten el seguimiento, enfermedad inflamatoria o autoinmune crónica, bronquiectasias graves, tuberculosis activa o cáncer. Todos libres de enfermedad respiratoria aguda 8 semanas antes.
- **Números.** "We studied 289 individuals (92 cases and 197 controls)". El registro de ClinicalTrials.gov dice 310 inscritos. La TC "could be obtained and interpreted in 231 participants (79.9%): 80 cases (87%) and 151 (77%) controls".
- **Edad y exposición.** Edad 45,8±3,5 años en casos y 43,3±4,4 en controles. Paquetes-año 24,8±13,7 en controles. La cifra de los casos aparece como 31,6±116,3, que parece errata y no debe usarse. DLCO 84,2±20,7 % en casos y 91,6±13,5 % en controles. FEV1 post-broncodilatador 97,7±14,9 % en controles.
- **Protocolo de TC.** El texto solo dice "A low-dose computed tomography (CT) of the chest was obtained in all participants". No da escáner, kernel, grosor ni nivel de inspiración. No revisé el material suplementario.
- **Quién lee y con qué criterio.** "The presence/absence of emphysema was determined qualitatively in the coordinating centre (Hospital Universitario Son Espases-IdISBa, Palma de Mallorca) by an experienced radiologist who was blinded to patient/control status." Es un solo lector, con presencia o ausencia cualitativa. El texto no cita Fleischner ni %LAA ni −950.
- **Enfisema.** "Emphysema was present in 61% of cases and, of note, in 32% of controls too (p<0.001)". En ECLIPSE fue 60 % de casos y 8 % de controles, y en COPDGene 29 % y 9 %.
- **Interpretación de los autores.** Los autores recuerdan que "we (and in ECLIPSE, but not in COPDGene) used low-dose radiation (which can overestimate the amount of quantitative emphysema)", y aun así concluyen que muestra "clear evidence of lung damage" en fumadores con espirometría normal.
- **Limitaciones citadas.** Muestra menor que los estudios epidemiológicos, posible sesgo de reclutamiento, y casos algo mayores que controles.

**Frase:** "En EARLY COPD un radiólogo ciego vio enfisema en el 32 % de fumadores con espirometría normal; nosotros lo cuantificamos y lo ponemos frente a una norma, porque esa lectura es cualitativa, de un solo lector y con protocolo de baja dosis."

## Referencias completas

1. Wasserthal J et al. Radiol Artif Intell 2023. doi:10.1148/ryai.230024
2. Isensee F et al. Nat Methods 2021. doi:10.1038/s41592-020-01008-z
3. Liu J et al. Sci Data 2025. doi:10.1038/s41597-025-06074-6
4. Arrigoni A et al. Radiol Med 2025. doi:10.1007/s11547-025-02166-w
5. Gevenois PA et al. Am J Respir Crit Care Med 1996;154:187. doi:10.1164/ajrccm.154.1.8680679
6. Lynch DA et al. Radiology 2015. doi:10.1148/radiol.2015141579
7. San José Estépar R et al. Am J Respir Crit Care Med 2025;211:709. doi:10.1164/rccm.202410-2012SO
8. QIBA CT Lung Densitometry Profile (RSNA). https://qibawiki.rsna.org/images/a/a8/QIBA_CT_Lung_Density_Profile_090420-clean.pdf
9. Boedeker KL et al. Radiology 2004;232:295. doi:10.1148/radiol.2321030383
10. Gierada DS et al. Acad Radiol 2010;17:146. PMID 19931472
11. Schilham AMR et al. IEEE Trans Med Imaging 2006. doi:10.1109/tmi.2006.871545
12. den Harder AM et al. Eur Radiol Exp 2018. doi:10.1186/s41747-018-0064-3
13. Gallardo-Estrella L et al. Eur Radiol 2016. doi:10.1007/s00330-015-3824-y
14. Bak SH et al. Eur Radiol 2020. doi:10.1007/s00330-020-07020-3
15. de Boer E et al. Insights Imaging 2019. doi:10.1186/s13244-019-0776-9
16. Sotoudeh-Paima S et al. Eur Radiol 2026. doi:10.1007/s00330-026-12800-4
17. Ashraf H et al. Thorax 2011. doi:10.1136/thx.2009.132688
18. Zach JA et al. J Thorac Imaging 2016. doi:10.1097/rti.0000000000000181
19. Stoel BC, Stolk J. Invest Radiol 2004. doi:10.1097/00004424-200411000-00006
20. Parr DG et al. Respir Res 2008. doi:10.1186/1465-9921-9-21
21. Kirby M et al. Am J Respir Crit Care Med 2018. doi:10.1164/rccm.201704-0692OC
22. Kirby M et al. ERJ Open Res 2021. doi:10.1183/23120541.00307-2021
23. Oelsner EC et al. Ann Am Thorac Soc 2018. doi:10.1513/annalsats.201710-820oc
24. Smith BM et al. JAMA 2020. doi:10.1001/jama.2020.6918
25. San José Estépar R et al. Am J Respir Crit Care Med 2013. doi:10.1164/rccm.201301-0162OC
26. Washko GR et al. Am J Respir Crit Care Med 2019. doi:10.1164/rccm.201811-2063OC
27. Pistenmaa CL et al. Chest 2021. doi:10.1016/j.chest.2021.01.084
28. Synn AJ et al. Ann Am Thorac Soc 2019. doi:10.1513/annalsats.201811-795oc
29. Mishima M et al. Proc Natl Acad Sci USA 1999. doi:10.1073/pnas.96.16.8829
30. Virdee S et al. Radiology 2021. doi:10.1148/radiol.2021210198
31. Vestal BE et al. Sci Rep 2023. doi:10.1038/s41598-023-40950-8
32. Quanjer PH et al. Eur Respir J 2012. doi:10.1183/09031936.00080312
33. Hoffman EA et al. Ann Am Thorac Soc 2014. doi:10.1513/annalsats.201310-364oc
34. Stoel BC et al. Respir Res 2019. doi:10.1186/s12931-019-1012-3
35. Marquand AF et al. Biol Psychiatry 2016. doi:10.1016/j.biopsych.2015.12.023
36. Bethlehem RAI et al. Nature 2022. doi:10.1038/s41586-022-04554-y
37. Han MK et al. Am J Respir Crit Care Med 2021;203:414. doi:10.1164/rccm.202008-3328PP
38. GOLD Report 2023. https://goldcopd.org/wp-content/uploads/2023/03/GOLD-2023-ver-1.3-17Feb2023_WMV.pdf
39. Harvey BG et al. Eur Respir J 2015. doi:10.1183/13993003.02377-2014
40. McAllister DA et al. PLoS One 2014. doi:10.1371/journal.pone.0093221
41. Wan ES et al. Am J Respir Crit Care Med 2018. doi:10.1164/rccm.201804-0663OC
42. Bhatt SP et al. JAMA 2025. doi:10.1001/jama.2025.7358
43. González G et al. Am J Respir Crit Care Med 2018. doi:10.1164/rccm.201705-0860oc
44. Balki I et al. Can Assoc Radiol J 2019. doi:10.1016/j.carj.2019.06.002
45. Riley RD et al. BMJ 2020. doi:10.1136/bmj.m441
46. Wang JM et al. Front Physiol 2023. doi:10.3389/fphys.2023.1144192
47. Dorosti T et al. Comput Biol Med 2025. doi:10.1016/j.compbiomed.2024.109533
48. Sarsembayeva T et al. J Imaging 2026. doi:10.3390/jimaging12010051
49. Huang SC et al. npj Digit Med 2020. doi:10.1038/s41746-020-00341-z
50. Stahlschmidt SR et al. Brief Bioinform 2022. doi:10.1093/bib/bbab569
51. Mohsen F et al. Sci Rep 2022. doi:10.1038/s41598-022-22514-4
52. Varma S, Simon R. BMC Bioinformatics 2006. doi:10.1186/1471-2105-7-91
53. Vabalas A et al. PLoS One 2019. doi:10.1371/journal.pone.0224365
54. Ojala M, Garriga GC. J Mach Learn Res 2010;11:1833. https://www.jmlr.org/papers/v11/ojala10a.html
55. Varoquaux G. NeuroImage 2018. doi:10.1016/j.neuroimage.2017.06.061
56. Cosío BG et al. ERJ Open Res 2020;6(4):00047-2020. doi:10.1183/23120541.00047-2020 (PMC7533304; NCT02352220)

## Para el equipo, antes de presentar

- **Resumen en lugar del artículo.** Las cifras salen de resúmenes y textos tal como los devolvió la herramienta de extracción, no de la lectura directa de los PDF. Para el punto 15 comprobé las citas con tres consultas distintas y coincidieron. Aun así, conviene abrir Cosío 2020 en PMC7533304 antes de citar entre comillas.
- **Sin referencia sólida:** validación independiente de TotalSegmentator en pulmón enfermo (1), referencias normativas de densidad TC para 35–50 años (10) y deep learning frente a TC cuantitativa en espirometría normal (12).
- **No citar:** Riley 2020 por su contenido [NV], los criterios menores exactos de Bhatt 2025 y la cifra de paquetes-año de los casos de Cosío.
