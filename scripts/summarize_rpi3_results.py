#!/usr/bin/env python3
"""Consolida las campañas de Raspberry Pi 3.

Lee los cinco ficheros optee_<algo>_rpi3_latest.json, construye un resumen
agregado y calcula tamaño y SHA-256 de los artefactos CA/TA compilados.
Genera optee_rpi3_summary_latest.{json,md} y
optee_artifact_metrics_rpi3_latest.{json,md}.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "documentacion" / "resultados"
EXAMPLES = ROOT / "laboratorio" / "optee" / "optee_examples"

ALGOS = ("ml_dsa", "ml_kem", "ecdsa", "hawk", "mayo")
UUID = {
    "ml_dsa": "7d1d3f76-9b55-4d7b-a708-c8c57e6fd1d8",
    "ml_kem": "d01a5091-c290-46dc-8a6f-e2088ece0d71",
    "ecdsa": "6b7658df-1cf5-4ecb-a2f5-09c8d51bcd58",
    "hawk": "d2c52f7c-9b84-444d-8ae9-3d8566ebe19c",
    "mayo": "b15a7c54-0f58-4f35-9a9d-c5a915e1a001",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_campaigns():
    summary = {"platform": "rpi3", "algorithms": {}}
    for algo in ALGOS:
        jpath = RESULTS / f"optee_{algo}_rpi3_latest.json"
        if not jpath.is_file():
            summary["algorithms"][algo] = {"missing": True}
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        entry = {
            "num_runs": data.get("num_runs"),
            "memory": data.get("memory", {}),
            "system_memory": data.get("system_memory", {}),
        }
        for key in data:
            if key.startswith("all_"):
                entry[key] = data[key]
        if "by_curve" in data:
            entry["by_curve"] = {
                curve: {m: s["mean_us"]
                        for m, s in block["stats"].items()}
                for curve, block in data["by_curve"].items()
            }
        elif "stats" in data:
            entry["means_us"] = {m: s["mean_us"]
                                 for m, s in data["stats"].items()}
        summary["algorithms"][algo] = entry
    return summary


def collect_artifacts():
    metrics = {}
    for algo in ALGOS:
        ca = EXAMPLES / algo / "host" / f"optee_example_{algo}"
        ta = EXAMPLES / algo / "ta" / f"{UUID[algo]}.ta"
        for name, path in ((f"{algo}_ca", ca), (f"{algo}_ta", ta)):
            if path.is_file():
                metrics[name] = {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            else:
                metrics[name] = {"path": str(path), "missing": True}
    return {"platform": "rpi3", "artifact_metrics": metrics}


def summary_md(summary):
    lines = ["# Resumen de campañas OP-TEE / Raspberry Pi 3", ""]
    for algo, entry in summary["algorithms"].items():
        lines.append(f"## {algo}")
        lines.append("")
        if entry.get("missing"):
            lines.append("- Campaña no disponible.")
            lines.append("")
            continue
        lines.append(f"- Repeticiones: {entry['num_runs']}")
        for key, val in entry.items():
            if key.startswith("all_"):
                lines.append(f"- {key}: {'sí' if val else 'no'}")
        if "means_us" in entry:
            lines.append("- Medias (us): " + ", ".join(
                f"{m}={v}" for m, v in entry["means_us"].items()))
        if "by_curve" in entry:
            for curve, means in entry["by_curve"].items():
                lines.append(f"- {curve} medias (us): " + ", ".join(
                    f"{m}={v}" for m, v in means.items()))
        mem = entry.get("memory", {})
        if mem.get("ta"):
            lines.append(
                f"- TA heap máx: {mem['ta']['heap_max_bytes']} B")
        if mem.get("ca"):
            lines.append(
                f"- CA VmHWM: {mem['ca']['vmhwm_kb']} kB")
        sysmem = entry.get("system_memory", {})
        if sysmem:
            lines.append(
                f"- Sistema, caída máx MemFree: "
                f"{sysmem.get('mem_free_peak_drop_kb')} kB")
        lines.append("")
    return "\n".join(lines)


def artifacts_md(data):
    lines = [
        "# Métricas de artefactos OP-TEE / Raspberry Pi 3",
        "",
        "Tamaños y hashes de los binarios CA/TA compilados para rpi3. "
        "Son tamaños de artefacto, no medidas de RAM ni de flash real.",
        "",
        "| Artefacto | Bytes | SHA-256 | Ruta |",
        "| --- | ---: | --- | --- |",
    ]
    for name, item in data["artifact_metrics"].items():
        if item.get("missing"):
            lines.append(f"| {name} | N/D | N/D | `{item['path']}` |")
        else:
            lines.append(
                f"| {name} | {item['bytes']} | `{item['sha256']}` | "
                f"`{item['path']}` |")
    lines.append("")
    return "\n".join(lines)


def main():
    summary = summarize_campaigns()
    artifacts = collect_artifacts()

    (RESULTS / "optee_rpi3_summary_latest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n", encoding="utf-8")
    (RESULTS / "optee_rpi3_summary_latest.md").write_text(
        summary_md(summary), encoding="utf-8")
    (RESULTS / "optee_artifact_metrics_rpi3_latest.json").write_text(
        json.dumps(artifacts, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n", encoding="utf-8")
    (RESULTS / "optee_artifact_metrics_rpi3_latest.md").write_text(
        artifacts_md(artifacts), encoding="utf-8")

    print("Resumen RPi3 escrito en:")
    print(f"  {RESULTS / 'optee_rpi3_summary_latest.json'}")
    print(f"  {RESULTS / 'optee_artifact_metrics_rpi3_latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
