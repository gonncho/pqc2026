#!/usr/bin/env bash
# Ejecuta las cinco campañas del TFG sobre la Raspberry Pi 3 y consolida
# el resumen agregado y las métricas de artefactos.
#
# Uso: ./run_rpi3_all.sh

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

ALGOS=(ml_dsa ml_kem ecdsa hawk mayo)
FAILED=()

for algo in "${ALGOS[@]}"; do
	echo "==================== $algo ===================="
	if ! "$SCRIPTS_DIR/run_rpi3_campaign.sh" "$algo"; then
		echo "[$algo] campaña fallida" >&2
		FAILED+=("$algo")
	fi
	echo
done

echo "==================== resumen ===================="
python3 "$SCRIPTS_DIR/summarize_rpi3_results.py"

if [ "${#FAILED[@]}" -gt 0 ]; then
	echo "Campañas con fallo: ${FAILED[*]}" >&2
	exit 1
fi
echo "Las cinco campañas se completaron."
