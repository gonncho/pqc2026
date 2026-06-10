# scripts/

Scripts de medición, despliegue y análisis. Todos los paths son relativos al
directorio raíz del repositorio, calculados desde la ubicación del propio script,
así que funcionan en cualquier máquina independientemente de dónde esté clonado
el repositorio.

---

## Scripts de shell

### `run_qemu_command.sh`

El script de bajo nivel que arranca QEMU. Regenera la imagen `rootfs.cpio.uboot`
si es necesario, construye los argumentos de QEMU (2 CPUs, 1 GB de RAM, VirtIO,
GICv3, modo seguro activado) y lanza el emulador mediante un script `expect` que
espera el prompt del sistema y ejecuta el comando que se le pasa como argumento.
No se llama directamente: lo invocan los scripts `run_qemu_<algo>.sh`.

### `run_qemu_<algo>.sh` (cinco scripts)

Un script por algoritmo (`ml_dsa`, `ml_kem`, `ecdsa`, `hawk`, `mayo`). Cada uno
llama a `run_qemu_command.sh` con el binario CA correspondiente, copia los logs
del puerto serie 0 y 1 con un timestamp, invoca el parser Python para generar
JSON y Markdown, y deja también un enlace `_latest` que siempre apunta a la
ejecución más reciente.

### `run_rpi3_campaign.sh`

Ejecuta una campaña sobre la Raspberry Pi 3 para el algoritmo que se le pasa
como argumento. Comprueba conectividad, copia `sample_meminfo.sh` a la Pi,
arranca el muestreador de memoria en segundo plano, ejecuta la CA (20
repeticiones), recoge el log y el CSV de vuelta al host y llama a
`parse_rpi3_campaign.py`.

Variables de entorno sobreescribibles:

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `RPI_HOST` | `raspberrypi.local` | Hostname o IP de la Pi |
| `RPI_USER` | `root` | Usuario SSH |
| `RPI_PASS` | `root` | Contraseña SSH |
| `MEMINFO_INTERVAL` | `0.1` | Intervalo de muestreo en segundos |

### `run_rpi3_all.sh`

Llama a `run_rpi3_campaign.sh` para los cinco algoritmos en secuencia y al
terminar invoca `summarize_rpi3_results.py` para generar el resumen agregado.
Si una campaña falla, registra el error pero continúa con las demás.

### `deploy_to_rpi3.sh`

Copia las TAs compiladas a `/lib/optee_armtz/` de la Pi y los binarios CA a
`/usr/bin/` mediante SCP. Sin argumentos despliega los cinco algoritmos. Con
argumentos despliega solo los indicados:

```bash
./scripts/deploy_to_rpi3.sh ml_dsa hawk
```

Acepta las mismas variables de entorno que `run_rpi3_campaign.sh`.

### `sample_meminfo.sh`

Muestreador de `/proc/meminfo` pensado para correr en la Pi durante una campaña.
Se copia automáticamente por `run_rpi3_campaign.sh`. Escribe un CSV con columnas
`t,MemFree,MemAvailable,Buffers,Cached,Slab` y termina al recibir SIGTERM.
Compatible con busybox.

---

## Scripts de Python

### `parse_<algo>_qemu_log.py` (cinco scripts)

Cada uno lee el log del puerto serie 0 de una campaña QEMU y extrae los tiempos
por operación (NOP, keygen, firma o encapsulación, verificación o decapsulación)
junto con metadatos del artefacto (tamaño del binario CA y TA, SHA-256). Produce
JSON por stdout y opcionalmente Markdown.

### `parse_rpi3_campaign.py`

Equivalente de los parsers QEMU pero para campañas en la Pi. Además de los
tiempos, extrae las métricas de memoria de la CA (VmPeak, VmHWM, VmRSS, VmData,
VmStk desde `/proc/<pid>/status`) y las estadísticas del heap de la TA reportadas
por OP-TEE.

### `summarize_qemu_results.py`

Lee los últimos JSON de todas las campañas QEMU y genera un resumen en tabla,
tanto en Markdown como en JSON, con todas las métricas de tiempo y tamaño de
artefacto en una sola vista.

### `summarize_rpi3_results.py`

Lo mismo para las campañas de la Pi. Incluye también el resumen de métricas de
memoria y los hashes de artefactos.

### `compare_qemu_vs_rpi3.py`

Alinea los resultados de ambas plataformas y calcula los ratios QEMU/RPi3 por
operación y algoritmo. Genera una tabla comparativa en Markdown, JSON y un
fichero `.tex` listo para incluir en LaTeX.

### `collect_artifact_metrics.py`

Lee el tamaño en bytes y el SHA-256 de cada CA y TA compilada y los guarda en
JSON y Markdown. Útil para confirmar que los binarios medidos corresponden a una
compilación concreta.

### `validate_latest_results.py`

Comprobación de sanidad sobre los últimos JSON de QEMU: verifica que todas las
métricas esperadas están presentes, que los valores son positivos y que la
verificación funcional pasó. Útil para detectar ejecuciones corruptas antes de
guardar los resultados.

### `fetch_nist_additional_signatures.py`

Descarga los paquetes de referencia de HAWK y MAYO desde el repositorio del NIST
(ronda 2 de firmas adicionales). No es necesario para compilar ni medir: sirve
para acceder a los vectores de test y la especificación oficial de cada algoritmo.
