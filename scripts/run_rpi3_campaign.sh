#!/usr/bin/env bash
# Ejecuta una campaña de un algoritmo sobre la Raspberry Pi 3 vía SSH.
# Lanza el muestreador de memoria del sistema en paralelo, ejecuta la CA
# instrumentada, recoge log y CSV, y genera JSON + Markdown con el parser.
#
# Uso: ./run_rpi3_campaign.sh <ml_dsa|ml_kem|ecdsa|hawk|mayo>

set -euo pipefail

ALGO="${1:-}"
case "$ALGO" in
	ml_dsa|ml_kem|ecdsa|hawk|mayo) ;;
	*) echo "Uso: $0 <ml_dsa|ml_kem|ecdsa|hawk|mayo>" >&2; exit 1 ;;
esac

RPI_HOST="${RPI_HOST:-raspberrypi.local}"
RPI_USER="${RPI_USER:-root}"
RPI_PASS="${RPI_PASS:-root}"
INTERVAL="${MEMINFO_INTERVAL:-0.1}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RESULTS_DIR="$ROOT_DIR/documentacion/resultados"
OPTEE="$ROOT_DIR/laboratorio/optee"
mkdir -p "$RESULTS_DIR"

SSH="sshpass -p $RPI_PASS ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o ServerAliveInterval=15 ${RPI_USER}@${RPI_HOST}"
SCP="sshpass -p $RPI_PASS scp -o StrictHostKeyChecking=no -o ConnectTimeout=15"

declare -A UUID=(
	[ml_dsa]=7d1d3f76-9b55-4d7b-a708-c8c57e6fd1d8
	[ml_kem]=d01a5091-c290-46dc-8a6f-e2088ece0d71
	[ecdsa]=6b7658df-1cf5-4ecb-a2f5-09c8d51bcd58
	[hawk]=d2c52f7c-9b84-444d-8ae9-3d8566ebe19c
	[mayo]=b15a7c54-0f58-4f35-9a9d-c5a915e1a001
)
uuid="${UUID[$ALGO]}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_STAMP="$RESULTS_DIR/optee_${ALGO}_rpi3_${STAMP}.log"
CSV_STAMP="$RESULTS_DIR/optee_${ALGO}_rpi3_${STAMP}.meminfo.csv"
JSON_STAMP="$RESULTS_DIR/optee_${ALGO}_rpi3_${STAMP}.json"
MD_STAMP="$RESULTS_DIR/optee_${ALGO}_rpi3_${STAMP}.md"
JSON_LATEST="$RESULTS_DIR/optee_${ALGO}_rpi3_latest.json"
MD_LATEST="$RESULTS_DIR/optee_${ALGO}_rpi3_latest.md"
LOG_LATEST="$RESULTS_DIR/optee_${ALGO}_rpi3_latest.log"
CSV_LATEST="$RESULTS_DIR/optee_${ALGO}_rpi3_latest.meminfo.csv"

echo "[$ALGO] comprobando conectividad con $RPI_HOST"
if ! ping -c 1 -W 3 "$RPI_HOST" >/dev/null 2>&1; then
	echo "[$ALGO] la Pi no responde al ping" >&2
	exit 1
fi

echo "[$ALGO] copiando muestreador de memoria a la Pi"
$SCP "$SCRIPTS_DIR/sample_meminfo.sh" "${RPI_USER}@${RPI_HOST}:/tmp/sample_meminfo.sh"
$SSH "chmod +x /tmp/sample_meminfo.sh"

echo "[$ALGO] ejecutando campaña (muestreo de memoria a ${INTERVAL}s)"
$SSH "ALGO=$ALGO INTERVAL=$INTERVAL sh -s" <<'REMOTE'
CSV=/tmp/rpi3_${ALGO}.meminfo.csv
LOG=/tmp/rpi3_${ALGO}.log
/tmp/sample_meminfo.sh "$CSV" "$INTERVAL" &
SAMPLER=$!
sleep 1
RC=0
/usr/bin/optee_example_${ALGO} > "$LOG" 2>&1 || RC=$?
kill "$SAMPLER" 2>/dev/null || true
wait "$SAMPLER" 2>/dev/null || true
sync
exit $RC
REMOTE

echo "[$ALGO] recogiendo log y CSV"
$SCP "${RPI_USER}@${RPI_HOST}:/tmp/rpi3_${ALGO}.log" "$LOG_STAMP"
$SCP "${RPI_USER}@${RPI_HOST}:/tmp/rpi3_${ALGO}.meminfo.csv" "$CSV_STAMP"

CA_ARTIFACT="$OPTEE/optee_examples/${ALGO}/host/optee_example_${ALGO}"
TA_ARTIFACT="$OPTEE/optee_examples/${ALGO}/ta/${uuid}.ta"

echo "[$ALGO] parseando resultados"
python3 "$SCRIPTS_DIR/parse_rpi3_campaign.py" "$ALGO" "$LOG_STAMP" \
	--meminfo "$CSV_STAMP" \
	--json "$JSON_STAMP" \
	--markdown "$MD_STAMP" \
	--artifact "ca=$CA_ARTIFACT" \
	--artifact "ta=$TA_ARTIFACT"

cp "$JSON_STAMP" "$JSON_LATEST"
cp "$MD_STAMP" "$MD_LATEST"
cp "$LOG_STAMP" "$LOG_LATEST"
cp "$CSV_STAMP" "$CSV_LATEST"

echo "[$ALGO] resultados guardados:"
echo "  $JSON_LATEST"
echo "  $MD_LATEST"
