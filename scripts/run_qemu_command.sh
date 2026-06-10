#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <command inside guest>" >&2
    exit 2
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPTEE_ROOT="$ROOT_DIR/laboratorio/optee"
BIN_DIR="$OPTEE_ROOT/out/bin"
QEMU_BIN="$OPTEE_ROOT/qemu/build/aarch64-softmmu/qemu-system-aarch64"
EXPECT_SCRIPT="$OPTEE_ROOT/build/qemu-run-command.exp"
ROOTFS_GZ="$OPTEE_ROOT/out-br/images/rootfs.cpio.gz"
ROOTFS_UBOOT="$BIN_DIR/rootfs.cpio.uboot"
MKIMAGE="$OPTEE_ROOT/u-boot/tools/mkimage"

export PATH="$OPTEE_ROOT/toolchains/aarch64/bin:$OPTEE_ROOT/toolchains/aarch32/bin:$OPTEE_ROOT/out-br/host/bin:$PATH"
unset LD_LIBRARY_PATH

ln -sf "$ROOTFS_GZ" "$BIN_DIR/rootfs.cpio.gz"
"$MKIMAGE" -A arm64 \
    -T ramdisk \
    -C gzip \
    -a 0x45000000 \
    -e 0x45000000 \
    -n "Root file system" \
    -d "$ROOTFS_GZ" "$ROOTFS_UBOOT" >/dev/null

QEMU_ARGS="-nographic"
QEMU_ARGS+=" -smp 2"
QEMU_ARGS+=" -cpu max,sme=on,pauth-impdef=on"
QEMU_ARGS+=" -d unimp -semihosting-config enable=on,target=native"
QEMU_ARGS+=" -m 1057"
QEMU_ARGS+=" -bios bl1.bin"
QEMU_ARGS+=" -initrd rootfs.cpio.gz"
QEMU_ARGS+=" -kernel Image"
QEMU_ARGS+=" -append 'console=ttyAMA0,38400 keep_bootcon root=/dev/vda2 '"
QEMU_ARGS+=" -object rng-random,filename=/dev/urandom,id=rng0"
QEMU_ARGS+=" -device virtio-rng-pci,rng=rng0,max-bytes=1024,period=1000"
QEMU_ARGS+=" -netdev user,id=vmnic"
QEMU_ARGS+=" -device virtio-net-device,netdev=vmnic"
QEMU_ARGS+=" -machine virt,acpi=off,secure=on,mte=off,gic-version=3,virtualization=false"
QEMU_ARGS+=" -serial mon:stdio -serial file:serial1.log"

cd "$BIN_DIR"
rm -f serial0.log serial1.log
QEMU="$QEMU_BIN" QEMU_RUN_CMD_ARGS="$QEMU_ARGS" expect "$EXPECT_SCRIPT" --command "$*"
