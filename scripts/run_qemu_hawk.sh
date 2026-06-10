#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/documentacion/resultados"
SERIAL0_LOG="$ROOT_DIR/laboratorio/optee/out/bin/serial0.log"
SERIAL1_LOG="$ROOT_DIR/laboratorio/optee/out/bin/serial1.log"
JSON_OUT="$RESULTS_DIR/optee_hawk_qemu_latest.json"
MD_OUT="$RESULTS_DIR/optee_hawk_qemu_latest.md"
SERIAL0_OUT="$RESULTS_DIR/optee_hawk_qemu_latest.serial0.log"
SERIAL1_OUT="$RESULTS_DIR/optee_hawk_qemu_latest.serial1.log"
CA_ARTIFACT="$ROOT_DIR/laboratorio/optee/out-br/target/usr/bin/optee_example_hawk"
TA_ARTIFACT="$ROOT_DIR/laboratorio/optee/out-br/target/lib/optee_armtz/d2c52f7c-9b84-444d-8ae9-3d8566ebe19c.ta"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
JSON_STAMP="$RESULTS_DIR/optee_hawk_qemu_${STAMP}.json"
MD_STAMP="$RESULTS_DIR/optee_hawk_qemu_${STAMP}.md"
SERIAL0_STAMP="$RESULTS_DIR/optee_hawk_qemu_${STAMP}.serial0.log"
SERIAL1_STAMP="$RESULTS_DIR/optee_hawk_qemu_${STAMP}.serial1.log"

mkdir -p "$RESULTS_DIR"

"$ROOT_DIR/scripts/run_qemu_command.sh" optee_example_hawk
cp "$SERIAL0_LOG" "$SERIAL0_STAMP"
cp "$SERIAL1_LOG" "$SERIAL1_STAMP"
"$ROOT_DIR/scripts/parse_hawk_qemu_log.py" "$SERIAL0_STAMP" \
    --markdown "$MD_STAMP" \
    --artifact "ca=$CA_ARTIFACT" \
    --artifact "ta=$TA_ARTIFACT" >"$JSON_STAMP"
cp "$JSON_STAMP" "$JSON_OUT"
cp "$MD_STAMP" "$MD_OUT"
cp "$SERIAL0_STAMP" "$SERIAL0_OUT"
cp "$SERIAL1_STAMP" "$SERIAL1_OUT"

echo "Resultados guardados en:"
echo "  $JSON_OUT"
echo "  $MD_OUT"
echo "  $SERIAL0_OUT"
echo "  $SERIAL1_OUT"
