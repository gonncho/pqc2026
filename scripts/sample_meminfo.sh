#!/bin/sh
# Muestreador de /proc/meminfo. Pensado para ejecutarse en la Raspberry Pi 3
# durante una campaña, en segundo plano. Escribe un CSV con una fila por
# muestra y termina al recibir SIGTERM. Compatible con busybox.
#
# Uso: sample_meminfo.sh [csv_salida] [intervalo_segundos]

OUT="${1:-/tmp/rpi3_meminfo.csv}"
INTERVAL="${2:-0.1}"

echo "t,MemFree,MemAvailable,Buffers,Cached,Slab" > "$OUT"

i=0
while true; do
	awk -v i="$i" '
		/^MemFree:/      { f = $2 }
		/^MemAvailable:/ { a = $2 }
		/^Buffers:/      { b = $2 }
		/^Cached:/       { c = $2 }
		/^Slab:/         { s = $2 }
		END { print i "," f "," a "," b "," c "," s }
	' /proc/meminfo >> "$OUT"
	i=$((i + 1))
	sleep "$INTERVAL"
done
