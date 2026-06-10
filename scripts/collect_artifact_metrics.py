#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = ROOT / "documentacion" / "resultados" / "optee_artifact_metrics_latest.json"
DEFAULT_OUTPUT_MD = ROOT / "documentacion" / "resultados" / "optee_artifact_metrics_latest.md"

ARTIFACTS = {
    "ml_dsa_ca": ROOT / "laboratorio/optee/out-br/target/usr/bin/optee_example_ml_dsa",
    "ml_dsa_ta": ROOT / "laboratorio/optee/out-br/target/lib/optee_armtz/7d1d3f76-9b55-4d7b-a708-c8c57e6fd1d8.ta",
    "ml_kem_ca": ROOT / "laboratorio/optee/out-br/target/usr/bin/optee_example_ml_kem",
    "ml_kem_ta": ROOT / "laboratorio/optee/out-br/target/lib/optee_armtz/d01a5091-c290-46dc-8a6f-e2088ece0d71.ta",
    "ecdsa_ca": ROOT / "laboratorio/optee/out-br/target/usr/bin/optee_example_ecdsa",
    "ecdsa_ta": ROOT / "laboratorio/optee/out-br/target/lib/optee_armtz/6b7658df-1cf5-4ecb-a2f5-09c8d51bcd58.ta",
    "hawk_ca": ROOT / "laboratorio/optee/out-br/target/usr/bin/optee_example_hawk",
    "hawk_ta": ROOT / "laboratorio/optee/out-br/target/lib/optee_armtz/d2c52f7c-9b84-444d-8ae9-3d8566ebe19c.ta",
    "mayo_ca": ROOT / "laboratorio/optee/out-br/target/usr/bin/optee_example_mayo",
    "mayo_ta": ROOT / "laboratorio/optee/out-br/target/lib/optee_armtz/b15a7c54-0f58-4f35-9a9d-c5a915e1a001.ta",
    "rootfs_cpio_gz": ROOT / "laboratorio/optee/out-br/images/rootfs.cpio.gz",
    "rootfs_cpio_uboot": ROOT / "laboratorio/optee/out/bin/rootfs.cpio.uboot",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect() -> dict:
    metrics = {}
    for name, path in ARTIFACTS.items():
        if path.is_file():
            stat = path.stat()
            metrics[name] = {
                "path": str(path),
                "bytes": stat.st_size,
                "sha256": sha256(path),
                "mtime_ns": stat.st_mtime_ns,
            }
        else:
            metrics[name] = {
                "path": str(path),
                "missing": True,
            }
    return {"artifact_metrics": metrics}


def to_markdown(data: dict) -> str:
    lines = [
        "# Metricas de artefactos OP-TEE/QEMU",
        "",
        "Estas metricas complementan las campanas temporales. Son tamanos y hashes de artefactos compilados, no RAM, flash real en hardware ni consumo.",
        "",
        "| Artefacto | Bytes | SHA-256 | Ruta |",
        "| --- | ---: | --- | --- |",
    ]
    for name, item in data["artifact_metrics"].items():
        if item.get("missing"):
            lines.append(f"| {name} | N/D | N/D | `{item['path']}` |")
        else:
            lines.append(
                f"| {name} | {item['bytes']} | `{item['sha256']}` | `{item['path']}` |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()

    data = collect()
    json_path = Path(args.json)
    md_path = Path(args.markdown)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(to_markdown(data), encoding="utf-8")
    print(f"artifact metrics written to {json_path}")
    print(f"artifact metrics markdown written to {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
