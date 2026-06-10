#!/usr/bin/env bash
# Despliega las TAs y CAs del TFG sobre la Raspberry Pi 3 vía SCP.
# Las TAs van a /lib/optee_armtz/ y los binarios CA a /usr/bin/.
# Uso: ./deploy_to_rpi3.sh [algoritmo ...]   (sin argumentos despliega los cinco)

set -euo pipefail

RPI_HOST="${RPI_HOST:-raspberrypi.local}"
RPI_USER="${RPI_USER:-root}"
RPI_PASS="${RPI_PASS:-root}"
OPTEE="${OPTEE:-$(cd "$(dirname "$0")/../laboratorio/optee" && pwd)}"
EXAMPLES="$OPTEE/optee_examples"

SSH="sshpass -p $RPI_PASS ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${RPI_USER}@${RPI_HOST}"
SCP="sshpass -p $RPI_PASS scp -o StrictHostKeyChecking=no -o ConnectTimeout=10"

declare -A UUID=(
  [ml_dsa]=7d1d3f76-9b55-4d7b-a708-c8c57e6fd1d8
  [ml_kem]=d01a5091-c290-46dc-8a6f-e2088ece0d71
  [ecdsa]=6b7658df-1cf5-4ecb-a2f5-09c8d51bcd58
  [hawk]=d2c52f7c-9b84-444d-8ae9-3d8566ebe19c
  [mayo]=b15a7c54-0f58-4f35-9a9d-c5a915e1a001
)

ALGOS=("$@")
[ ${#ALGOS[@]} -eq 0 ] && ALGOS=(ml_dsa ml_kem ecdsa hawk mayo)

echo "Despliegue sobre ${RPI_USER}@${RPI_HOST}"
for algo in "${ALGOS[@]}"; do
  uuid="${UUID[$algo]:-}"
  [ -z "$uuid" ] && { echo "  $algo: algoritmo desconocido"; continue; }
  ta="$EXAMPLES/$algo/ta/$uuid.ta"
  ca="$EXAMPLES/$algo/host/optee_example_$algo"
  [ -f "$ta" ] || { echo "  $algo: falta TA $ta"; exit 1; }
  [ -f "$ca" ] || { echo "  $algo: falta CA $ca"; exit 1; }
  echo "  $algo -> TA $uuid.ta + CA optee_example_$algo"
  $SCP "$ta" "${RPI_USER}@${RPI_HOST}:/lib/optee_armtz/"
  $SCP "$ca" "${RPI_USER}@${RPI_HOST}:/usr/bin/optee_example_$algo"
  $SSH "chmod 444 /lib/optee_armtz/$uuid.ta && chmod 755 /usr/bin/optee_example_$algo"
done

echo "Verificación en la Pi:"
for algo in "${ALGOS[@]}"; do
  uuid="${UUID[$algo]:-}"
  $SSH "ls -la /lib/optee_armtz/$uuid.ta /usr/bin/optee_example_$algo" 2>/dev/null \
    && echo "  $algo: presente" || echo "  $algo: NO encontrado"
done
echo "Despliegue completado."
