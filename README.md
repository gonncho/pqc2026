# pqc2026

Scripts y configuración utilizados para medir el rendimiento de algoritmos de criptografía post-cuántica dentro de Trusted Execution Environments (TEE) con OP-TEE, tanto en QEMU (ARM v8) como en una Raspberry Pi 3 (Cortex-A53). Es el material de reproducibilidad del Trabajo Fin de Grado "Integración y evaluación de algoritmos post-cuánticos en Trusted Execution Environments sobre OP-TEE" (Universidad de Murcia, 2026).

Los cinco algoritmos evaluados son ML-DSA-65 (FIPS 204), ML-KEM-768 (FIPS 203), HAWK-512, MAYO_1 y ECDSA P-256 como línea base clásica. Cada uno está empaquetado como una Trusted Application (TA) de OP-TEE y su correspondiente Client Application (CA).

---

## Estructura del repositorio

```
.
├── scripts/                        scripts de medición y análisis
│   ├── run_qemu_<algo>.sh          lanza una campaña QEMU para <algo>
│   ├── run_qemu_command.sh         arranque de QEMU y captura de logs
│   ├── run_rpi3_campaign.sh        campaña sobre la Pi por SSH
│   ├── run_rpi3_all.sh             las cinco campañas de la Pi en secuencia
│   ├── deploy_to_rpi3.sh           copia TAs y CAs a la Pi por SCP
│   ├── sample_meminfo.sh           muestreador de /proc/meminfo (corre en la Pi)
│   ├── parse_<algo>_qemu_log.py    parser de log QEMU por algoritmo
│   ├── parse_rpi3_campaign.py      parser de log de campaña en la Pi
│   ├── summarize_qemu_results.py   resumen agregado de QEMU
│   ├── summarize_rpi3_results.py   resumen agregado de la Pi
│   ├── compare_qemu_vs_rpi3.py     comparación entre plataformas
│   ├── collect_artifact_metrics.py tamaño y SHA-256 de TAs y CAs
│   └── validate_latest_results.py  comprobación de consistencia de resultados
├── lanzar_optee.sh                 lanzador interactivo de QEMU (abre los dos mundos)
└── laboratorio/
    ├── iot5g-tee-lab/              guía de laboratorio y scripts de paths
    └── optee/                      árbol fuente completo de OP-TEE (gestionado con repo)
        ├── build/                  makefiles de plataforma (qemu_v8.mk, rpi3.mk, ...)
        ├── optee_os/               sistema operativo del Mundo Seguro
        ├── optee_client/           libteec y tee-supplicant
        └── optee_examples/         las cinco TAs y CAs desarrolladas para el TFG
```

---

## Requisitos

**Host de compilación:** Ubuntu 22.04 o 24.04 (x86-64). Otras distribuciones funcionan pero los nombres de paquetes pueden variar.

**Paquetes:**

```bash
sudo apt install git python3 python3-pip repo expect sshpass \
     gcc-aarch64-linux-gnu gcc-arm-linux-gnueabihf \
     qemu-system-arm libglib2.0-dev libpixman-1-dev \
     u-boot-tools device-tree-compiler xterm bc flex bison \
     libssl-dev libncurses-dev ninja-build
```

**Dependencias de Python** (solo para los scripts de análisis):

```bash
pip install prettytable tabulate
```

**Raspberry Pi 3:** imagen de OP-TEE grabada en la tarjeta SD con `tee-supplicant` activo al arrancar. El apartado de compilación siguiente describe cómo generarla.

---

## Compilación del ecosistema OP-TEE

El árbol fuente se gestiona con la herramienta `repo` de Google. Para una instalación desde cero:

```bash
mkdir optee && cd optee
repo init -u https://github.com/OP-TEE/manifest.git -m qemu_v8.xml -b 4.4.0
repo sync -j4 --no-clone-bundle
```

### QEMU (ARM v8)

```bash
# Aplicar los fixes de path del laboratorio (solo la primera vez)
cd laboratorio/iot5g-tee-lab
./run-pathfixes.sh
./run-toolchainsinpath.sh

# Compilar todo para QEMU
cd ../optee/build
make PLATFORM=qemu_v8 toolchains
make PLATFORM=qemu_v8 all
```

La primera compilación completa tarda entre 30 y 40 minutos. Las recompilaciones incrementales tras modificar una TA o CA son mucho más rápidas.

### Raspberry Pi 3

```bash
cd laboratorio/optee/build
make PLATFORM=rpi3 toolchains
make PLATFORM=rpi3 all
```

Graba la imagen resultante en la SD, arranca la Pi y confirma que `tee-supplicant` está activo:

```bash
ssh root@<ip-de-la-pi> "ps aux | grep tee-supplicant"
```

---

## Desarrollo de TAs y CAs

Cada algoritmo tiene su directorio bajo `laboratorio/optee/optee_examples/<algo>/`:

```
<algo>/
├── host/       Client Application (Mundo Normal, espacio de usuario Linux)
│   ├── main.c
│   └── Makefile
└── ta/         Trusted Application (Mundo Seguro, kernel de OP-TEE)
    ├── <uuid>.c
    ├── include/
    ├── sub.mk
    └── Makefile
```

UUID asignado a cada TA:

| Algoritmo | UUID |
|-----------|------|
| ML-DSA-65 | `7d1d3f76-9b55-4d7b-a708-c8c57e6fd1d8` |
| ML-KEM-768 | `d01a5091-c290-46dc-8a6f-e2088ece0d71` |
| ECDSA P-256 | `6b7658df-1cf5-4ecb-a2f5-09c8d51bcd58` |
| HAWK-512 | `d2c52f7c-9b84-444d-8ae9-3d8566ebe19c` |
| MAYO_1 | `b15a7c54-0f58-4f35-9a9d-c5a915e1a001` |

Para recompilar un par TA+CA concreto tras la compilación inicial:

```bash
OPTEE=laboratorio/optee
export CROSS_COMPILE=$OPTEE/toolchains/aarch64/bin/aarch64-linux-gnu-
export TA_DEV_KIT_DIR=$OPTEE/optee_os/out/arm/export-ta_arm64
export TEEC_EXPORT=$OPTEE/optee_client/out/export/usr

make -C $OPTEE/optee_examples/ml_dsa clean
make -C $OPTEE/optee_examples/ml_dsa
```

Las implementaciones criptográficas provienen de [PQClean](https://github.com/PQClean/PQClean) (C portable, sin ensamblador específico de arquitectura). ECDSA usa la biblioteca [micro-ecc](https://github.com/kmackay/micro-ecc) compilada dentro de la TA en lugar de la API criptográfica GP de OP-TEE, ya que esta última mostró una sobrecarga de un orden de magnitud en las pruebas preliminares.

---

## Ejecución de mediciones

### Campañas en QEMU

Cada script arranca QEMU, ejecuta la CA, parsea el log serie y guarda los resultados en `documentacion/resultados/`.

```bash
# Algoritmos individuales
./scripts/run_qemu_ml_dsa.sh
./scripts/run_qemu_ml_kem.sh
./scripts/run_qemu_ecdsa.sh
./scripts/run_qemu_hawk.sh
./scripts/run_qemu_mayo.sh

# Resumen agregado
python3 scripts/summarize_qemu_results.py
```

### Campañas en Raspberry Pi 3

```bash
# Parámetros de conexión (por defecto 192.168.18.223, root/root)
export RPI_HOST=192.168.x.x
export RPI_USER=root
export RPI_PASS=root

# Desplegar TAs y CAs en la Pi
./scripts/deploy_to_rpi3.sh

# Una campaña individual
./scripts/run_rpi3_campaign.sh ml_dsa

# Las cinco campañas y el resumen consolidado
./scripts/run_rpi3_all.sh
```

El script de campaña:
1. comprueba conectividad con la Pi por ping
2. copia `sample_meminfo.sh` a `/tmp/` de la Pi
3. arranca el muestreador de `/proc/meminfo` en segundo plano (intervalo 0,1 s)
4. ejecuta `optee_example_<algo>` (20 repeticiones)
5. detiene el muestreador y recoge el log y el CSV
6. ejecuta el parser para generar JSON y Markdown

### Archivos de salida

Los resultados se guardan en `documentacion/resultados/`:

```
optee_<algo>_<plataforma>_<timestamp>.log          salida bruta de la CA
optee_<algo>_<plataforma>_<timestamp>.json         métricas estructuradas
optee_<algo>_<plataforma>_<timestamp>.md           resumen legible
optee_<algo>_rpi3_<timestamp>.meminfo.csv          muestras de memoria
optee_<algo>_<plataforma>_latest.*                 última ejecución
optee_rpi3_summary_latest.{json,md}               resumen entre algoritmos
optee_artifact_metrics_*.{json,md}                tamaños y hashes de artefactos
```

---

## Métricas recogidas

Cada CA realiza 20 repeticiones consecutivas y registra:

- `nop_us`: ida y vuelta con un comando vacío, para medir el coste de la infraestructura TEE sin carga criptográfica
- `fresh_session_nop_us`: lo mismo pero abriendo y cerrando sesión en cada llamada, para aislar el coste de apertura de sesión
- `keygen_us`, `sign_us` / `encaps_us`, `verify_us` / `decaps_us`: las tres operaciones criptográficas

Se reportan media, mínimo, máximo y desviación típica para cada métrica. La corrección funcional (todas las verificaciones o todos los secretos compartidos son correctos) se registra por separado.

En la Pi también se captura memoria de la CA desde `/proc/<pid>/status` (VmPeak, VmHWM, VmRSS, VmData, VmStk) y estadísticas del heap de la TA reportadas por OP-TEE.

---

## Comparación entre plataformas

```bash
python3 scripts/compare_qemu_vs_rpi3.py
```

Genera una tabla de ratios de aceleración (tiempo QEMU / tiempo RPi3) por algoritmo y operación. QEMU tiende a ser optimista en cómputo (0,4-0,6 veces el tiempo de la Pi) y pesimista en latencia del TEE (2-4 veces el NOP). El orden relativo entre algoritmos se mantiene entre plataformas.

---

## Notas de reproducibilidad

- La versión de OP-TEE utilizada es **4.4.0** con los manifiestos `qemu_v8` y `rpi3`.
- Las implementaciones de PQClean están incluidas dentro de cada directorio de TA para evitar desfase de versiones.
- Las 20 repeticiones son un compromiso entre varianza de medida (la Pi no tiene aceleración criptográfica por hardware, así que los tiempos son largos) y tiempo total de experimento. Reducir el número de repeticiones amplía los intervalos de confianza de forma notable, especialmente en keygen de HAWK.


---

## Licencia

Los scripts y TAs desarrollados para este proyecto se distribuyen bajo la licencia BSD 2-Clause. Los componentes de OP-TEE conservan sus licencias originales (BSD 2-Clause para optee_os y optee_client, GPL-2.0 para el driver de Linux).

---

## Contacto

Gonzalo Vicente Pérez - gonzalo.vicentep@um.es
