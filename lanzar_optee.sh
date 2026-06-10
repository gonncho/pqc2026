#!/bin/bash
# lanzar_optee.sh
# Arranca el escenario OP-TEE + QEMU ARM v8 con un solo click.
# Los dos mundos (Normal World y Secure World) se abren en ventanas separadas.

OPTEE_ROOT="$(cd "$(dirname "$0")/laboratorio/optee" && pwd)"
BUILD_DIR="$OPTEE_ROOT/build"
BINARIES="$OPTEE_ROOT/out/bin"

export PATH="$OPTEE_ROOT/toolchains/aarch64/bin:$OPTEE_ROOT/toolchains/aarch32/bin:$PATH"
unset LD_LIBRARY_PATH

# Regenerar uImage y rootfs.cpio.uboot si no existen o si Image es más reciente
if [ ! -f "$BINARIES/uImage" ] || [ "$BINARIES/Image" -nt "$BINARIES/uImage" ]; then
    echo "[*] Generando uImage..."
    mkimage -A arm64 -O linux -T kernel -C none \
        -a 0x42200000 -e 0x42200000 \
        -n "Linux" -d "$BINARIES/Image" "$BINARIES/uImage"
fi

if [ ! -f "$BINARIES/rootfs.cpio.uboot" ] || [ "$BINARIES/rootfs.cpio.gz" -nt "$BINARIES/rootfs.cpio.uboot" ]; then
    echo "[*] Generando rootfs.cpio.uboot..."
    mkimage -A arm64 -O linux -T ramdisk -C gzip \
        -a 0x45000000 -e 0x45000000 \
        -n "initrd" -d "$BINARIES/rootfs.cpio.gz" "$BINARIES/rootfs.cpio.uboot"
fi

# Matar cualquier instancia QEMU anterior para liberar puertos
pkill -f qemu-system-aarch64 2>/dev/null; sleep 0.5

cd "$BUILD_DIR"

# Lanzar QEMU y responder automáticamente al prompt del monitor con 'c'
expect -c "
    set timeout 60
    spawn make PLATFORM=qemu_v8 RUST_ENABLE=n run-only
    expect {
        \"(qemu)\" { send \"c\r\"; interact }
        timeout     { puts \"[ERROR] Timeout esperando al monitor QEMU\"; exit 1 }
    }
"
