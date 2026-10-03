# Trabajar en MareNostrum 5

Los nodos de MareNostrum no tienen salida a internet. No hay `pip install` ni
descarga de pesos. Por eso todo viaja en un directorio `bundle/` que lleva un
Python autónomo con las dependencias y los pesos de los modelos.

## 1. Preparar el bundle (en una máquina con internet)

```bash
./mn5/build_bundle.sh        # Python 3.12 autónomo con todo mn5/requirements.txt
./mn5/fetch_weights.sh       # pesos de lungmask, TotalSegmentator, ResNet y CT-FM
tar -cf maps-bundle.tar bundle
```

El intérprete es python-build-standalone, que funciona desde cualquier
directorio. `torch` va compilado con CUDA 12.1 porque acepta drivers NVIDIA más
antiguos que las versiones nuevas.

## 2. Subirlo

Las transferencias entran por la máquina de transferencia, no por los logins.
No reintentes la contraseña si falla: el BSC bloquea la conexión de toda la sede.

```bash
rsync -avP maps-bundle.tar <usuario>@transfer1.bsc.es:/gpfs/scratch/<grupo>/<usuario>/
```

En MareNostrum:

```bash
cd /gpfs/scratch/<grupo>/<usuario>
git clone https://github.com/<equipo>/<repo>.git maps && cd maps
tar -xf ../maps-bundle.tar            # deja bundle/ dentro del repo
source mn5/env.sh
```

## 3. Comprobar antes de nada

```bash
python3 -c "import torch, lungmask, totalsegmentator; print(torch.__version__)"
python3 -m pytest -q
bsc_queues                            # colas y límites de la cuenta
bsc_quota
salloc -A <cuenta> -q acc_interactive -t 00:30:00 --gres=gpu:1 -c 20
nvidia-smi && python3 -c "import torch; print(torch.cuda.is_available())"
```

Si `torch.cuda.is_available()` da `False` con GPU asignada, el driver es más
antiguo de lo previsto. El pipeline funciona en CPU, más lento.

## 4. Procesar la cohorte

```bash
mkdir -p logs outputs
python3 scripts/inventory.py <datos del reto> --out outputs/inventario.csv
python3 scripts/make_manifest.py outputs/inventario.csv --out outputs/manifiesto.csv
N=$(($(wc -l < outputs/manifiesto.csv) - 1))
sbatch -A <cuenta> -q <cola> --array=1-$N%16 mn5/extract_array.sbatch outputs/manifiesto.csv outputs/cohorte
python3 scripts/collect_cohort.py outputs/cohorte
```

Mira el inventario antes de generar el manifiesto. Dice qué kernels, grosores y
fabricantes hay, y si cada paciente tiene una serie o varias. Si hay inspiración
y espiración, filtra con `--descripcion`.

Cada TC escribe en `outputs/cohorte/sujetos/<id>/`. Una tarea que falla se
relanza sola con `--array=<k>`. Las ya procesadas se saltan.

## 5. Ver la app desde el portátil

Los logins matan los procesos que pasan de 5 minutos de CPU, así que la app
corre en un nodo de cómputo.

```bash
salloc -A <cuenta> -q acc_interactive -t 02:00:00 -c 20
hostname                              # apunta el nombre del nodo
python3 -m streamlit run app/maps_app.py --server.headless true \
  --browser.gatherUsageStats false --server.port 8501 -- --cohort outputs/cohorte
```

En el portátil:

```bash
ssh -L 8501:<nodo>:8501 <usuario>@alogin1.bsc.es
```

y abre `http://localhost:8501`.

## Lo que no está comprobado

Las colas, la cuenta y la versión del driver de la hackathon no se conocen hasta
entrar. Este documento sale de la documentación pública del BSC.
