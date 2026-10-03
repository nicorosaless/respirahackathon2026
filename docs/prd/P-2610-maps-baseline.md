# P-2610-maps-baseline: solución propuesta para el reto MAPS

> Primera propuesta, anterior a los datos reales. El modelo vigente está en
> `docs/modelo.md`.

## El problema

El reto pide detectar daño pulmonar en personas que aún no cumplen el criterio
espirométrico de EPOC (FEV1/FVC < 0,7), a partir de la TC y de datos clínicos y
biológicos. Los cambios en la TC son pequeños y la cohorte será pequeña.

Dos consecuencias marcan el diseño. Con pocos sujetos no se puede entrenar una
red de extremo a extremo, así que la red tiene que venir preentrenada y quedar
congelada. Y un índice global por paciente no basta para un clínico: hace falta
decir dónde está el daño.

## Qué se propone

1. **Segmentar pulmón y lóbulos** con un modelo preentrenado (lungmask). Es
   automático y no depende de quien lea la TC.
2. **Calcular la densitometría clásica por lóbulo**: %LAA-950, %LAA-910, Perc15,
   áreas de alta atenuación. Es la referencia que cualquier modelo profundo
   tiene que superar.
3. **Mapa de daño con etiquetas débiles.** Una ResNet-50 preentrenada y
   congelada da un embedding por celda de 3 mm. Cada celda hereda la etiqueta
   clínica de su sujeto, referencia o enfermedad establecida, y se ajusta un
   modelo lineal. Aplicado a un sujeto con EPOC precoz dice qué zonas se parecen
   al tejido enfermo. Nadie dibuja lesiones.
4. **Integrar por bloques.** Clínica, biología, densitometría y resumen del mapa
   son bloques de variables por sujeto. `maps.fusion.compare_blocks` da el AUC
   fuera de muestra de cada bloque y de la fusión con la misma validación, y con
   eso se ve qué añade la imagen sobre la clínica.
5. **Informe por paciente.** Cortes coronales con el mapa superpuesto y la tabla
   por lóbulo. Es la prueba de concepto que se enseña.

## Por qué esta forma y no otra

El experimento previo en `docs/experimento-resnet.md` descartó la variante normativa, la que no
usa ninguna etiqueta: marca vasos e hilio y no detecta enfisema mínimo. La
variante con etiquetas débiles sí lo detecta, con AUC 0,81 en sujetos no vistos.

El mismo experimento avisa de que ese mapa correlaciona -0,95 con Perc15. En la
hackathon hay que comprobar si la ResNet aporta algo más que densidad, con dos
pruebas concretas: el AUC de la fusión frente al de la densitometría sola, y el
mapa recalculado sobre la TC con la densidad media de cada sujeto restada.

## Plan para el día de la hackathon

1. Pasar `scripts/run_volume.py` por todas las TC y juntar las tablas por lóbulo.
   Son 2,5 min por TC en CPU y 30 s con la GPU.
2. Fijar con el equipo clínico quién es referencia y quién enfermedad
   establecida. Candidatos para EPOC precoz según GOLD 2023: FEV1/FVC >= 0,7 con
   síntomas, con DLCO bajo, con atrapamiento aéreo o con caída rápida del FEV1.
3. Reentrenar el modelo de parches con esa cohorte. El entrenado con la base
   pública no sirve en otro escáner.
4. Comparar bloques: clínica sola, clínica más densitometría, clínica más
   densitometría más mapa.
5. Preparar el informe de tres pacientes: uno de referencia, uno con EPOC
   precoz y uno con EPOC establecida.

## Riesgos

- **Escáner, kernel y dosis.** Cambian la textura más que la enfermedad
  temprana. Si la cohorte mezcla protocolos, hay que estratificar o incluir el
  protocolo como covariable, y comprobar que el modelo no predice el escáner.
- **Volumen de inspiración.** Un pulmón menos hinchado es más denso. Sin TC en
  espiración no se puede medir atrapamiento aéreo.
- **Edad, sexo y talla.** La densidad pulmonar depende de las tres. Van en el
  bloque clínico para que el mapa no las cobre como daño.
- **Cohorte pequeña.** Los intervalos del experimento previo tienen 0,3 de
  ancho con 39 sujetos. Toda comparación se hace remuestreando sujetos.
- **Referencia mal definida.** Si los controles son fumadores, el modelo
  aprende a distinguir fumadores con y sin obstrucción, que es otra pregunta.

## Fuera de alcance

Medidas de vía aérea (Pi10, grosor de pared), poda vascular, registro
inspiración-espiración y entrenamiento de redes 3D. Las tres primeras tienen
valor en EPOC precoz y serían el siguiente paso si los datos las permiten.

## Cómo se comprueba que funciona

- `uv run pytest -q` pasa.
- `scripts/exp_slices.py` y `scripts/report_slices.py` reproducen la tabla de
  `docs/experimento-resnet.md` sobre datos públicos.
- `scripts/run_volume.py` deja una tabla por lóbulo y una figura a partir de una
  serie DICOM.
