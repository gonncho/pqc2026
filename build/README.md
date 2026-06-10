# build/

Makefiles de plataforma y scripts auxiliares del sistema de build de OP-TEE.
Son copias de los ficheros originales del repositorio
[OP-TEE/build](https://github.com/OP-TEE/build) (versión 4.4.0), incluidos aquí
para que quede constancia de la configuración exacta usada en el proyecto.

Si clonas el árbol completo de OP-TEE con `repo sync`, estos ficheros ya estarán
en `laboratorio/optee/build/`. Los que están aquí son los mismos, sin modificar.

---

## Makefiles de plataforma

### `qemu_v8.mk`

Configuración de la plataforma QEMU ARM v8. Define la arquitectura de
compilación (AArch64 para el Mundo Normal y el Mundo Seguro), la plataforma de
OP-TEE OS (`vexpress-qemu_armv8a`), las opciones de QEMU (número de CPUs, RAM,
dispositivos VirtIO, GICv3) y los targets del build como `run-only` para
arrancar el emulador sin recompilar.

### `rpi3.mk`

Configuración de la plataforma Raspberry Pi 3. Compila en AArch64 para todos
los componentes. Incluye los paquetes de red (dhcpcd, ethtool) y SSH (openssh,
xinetd) en el rootfs de Buildroot para poder acceder a la Pi por SSH desde el
host una vez arrancada.

### `common.mk`

Lógica compartida por todos los makefiles de plataforma: targets para compilar
cada componente por separado (arm-tf, optee-os, optee-client, optee-examples,
buildroot, u-boot, qemu), reglas de limpieza y el target principal `all` que
los encadena en orden.

### `toolchain.mk`

Descarga automática de los toolchains cruzados aarch64 y aarch32 desde
Linaro. Define las rutas de instalación bajo `laboratorio/optee/toolchains/`
y el target `toolchains` que descarga y descomprime los archivos si no están
ya presentes.

---

## Scripts expect

### `qemu-run-command.exp`

Script Tcl/Expect que automatiza la interacción con QEMU: espera a que el
sistema arranque, espera el prompt de login en el Mundo Normal, ejecuta el
comando que se le pasa como argumento y captura la salida. Es el mecanismo que
permite lanzar campañas de medición no interactivas sobre QEMU.

### `qemu-check.exp`

Versión simplificada del anterior usada por el sistema de CI de OP-TEE para
comprobar que el arranque de QEMU llega a un estado correcto. No se usa
directamente en las campañas de medición.
