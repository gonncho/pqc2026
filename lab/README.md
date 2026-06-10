# lab/

Scripts de preparación del entorno de laboratorio. Son los únicos ficheros de
este repositorio que pueden necesitar ejecutarse con rutas absolutas, ya que
modifican el PATH del shell actual mediante `source`.

---

## `run-pathfixes.sh`

Elimina del PATH las rutas bajo `/mnt/` que pueden interferir con el build de
OP-TEE en sistemas con montajes externos (discos WSL2, unidades Samba, etc.).
Hay que ejecutarlo antes del primer build o cuando el build falle con errores
de herramienta no encontrada:

```bash
source lab/run-pathfixes.sh
```

## `run-toolchainsinpath.sh`

Añade los toolchains cruzados de OP-TEE al PATH del shell actual:

- `laboratorio/optee/toolchains/aarch64/bin` (compilador para el Mundo Normal y Mundo Seguro en AArch64)
- `laboratorio/optee/toolchains/aarch32/bin` (compilador para el Mundo Seguro en AArch32, necesario para TAs de 32 bits)

```bash
source lab/run-toolchainsinpath.sh
```

Requiere que el target `toolchains` del build se haya ejecutado previamente
para que los toolchains estén descargados:

```bash
make -C laboratorio/optee/build PLATFORM=qemu_v8 toolchains
```
