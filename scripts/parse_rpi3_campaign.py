#!/usr/bin/env python3
"""Parser de campañas OP-TEE sobre Raspberry Pi 3.

Extrae de un log de campaña los tiempos por operación, las banderas de éxito
funcional, la memoria de la CA (/proc/self/status), la memoria de la TA
(malloc_get_stats) y, si se aporta, los deltas de memoria del sistema a partir
de un CSV de muestreo de /proc/meminfo.

Cubre los cinco algoritmos del TFG. Los parsers QEMU originales se mantienen
sin cambios como bloque cerrado; este parser es específico de la fase física.
"""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path


# Configuración por algoritmo: métricas de tiempo y campo de éxito funcional.
ALGOS = {
    "ml_dsa": {
        "metrics": ("nop_us", "fresh_session_nop_us", "keygen_us",
                    "sign_us", "verify_us"),
        "success_field": "verify_ok",
        "curves": None,
        "run_re": re.compile(
            r"Run (?P<run>\d+): nop=(?P<nop_us>\d+) us "
            r"fresh_session_nop=(?P<fresh_session_nop_us>\d+) us "
            r"keygen=(?P<keygen_us>\d+) us sign=(?P<sign_us>\d+) us "
            r"verify=(?P<verify_us>\d+) us verify_ok=(?P<verify_ok>\d+)"),
    },
    "hawk": {
        "metrics": ("nop_us", "fresh_session_nop_us", "keygen_us",
                    "sign_us", "verify_us"),
        "success_field": "verify_ok",
        "curves": None,
        "run_re": re.compile(
            r"Run (?P<run>\d+): nop=(?P<nop_us>\d+) us "
            r"fresh_session_nop=(?P<fresh_session_nop_us>\d+) us "
            r"keygen=(?P<keygen_us>\d+) us sign=(?P<sign_us>\d+) us "
            r"verify=(?P<verify_us>\d+) us verify_ok=(?P<verify_ok>\d+)"),
    },
    "mayo": {
        "metrics": ("nop_us", "fresh_session_nop_us", "keygen_us",
                    "sign_us", "verify_us"),
        "success_field": "verify_ok",
        "curves": None,
        "run_re": re.compile(
            r"Run (?P<run>\d+): nop=(?P<nop_us>\d+) us "
            r"fresh_session_nop=(?P<fresh_session_nop_us>\d+) us "
            r"keygen=(?P<keygen_us>\d+) us sign=(?P<sign_us>\d+) us "
            r"verify=(?P<verify_us>\d+) us verify_ok=(?P<verify_ok>\d+)"),
    },
    "ml_kem": {
        "metrics": ("nop_us", "fresh_session_nop_us", "keygen_us",
                    "encaps_us", "decaps_us"),
        "success_field": "shared_secret_ok",
        "curves": None,
        "run_re": re.compile(
            r"Run (?P<run>\d+): nop=(?P<nop_us>\d+) us "
            r"fresh_session_nop=(?P<fresh_session_nop_us>\d+) us "
            r"keygen=(?P<keygen_us>\d+) us encaps=(?P<encaps_us>\d+) us "
            r"decaps=(?P<decaps_us>\d+) us "
            r"shared_secret_ok=(?P<shared_secret_ok>\d+)"),
    },
    "ecdsa": {
        "metrics": ("nop_us", "fresh_session_nop_us", "keygen_us",
                    "sign_us", "verify_us"),
        "success_field": "verify_ok",
        "curves": ("P-256", "P-384"),
        "run_re": re.compile(
            r"Run (?P<curve>P-256|P-384) (?P<run>\d+): "
            r"nop=(?P<nop_us>\d+) us "
            r"fresh_session_nop=(?P<fresh_session_nop_us>\d+) us "
            r"keygen=(?P<keygen_us>\d+) us sign=(?P<sign_us>\d+) us "
            r"verify=(?P<verify_us>\d+) us verify_ok=(?P<verify_ok>\d+)"),
    },
}

MEM_RE = re.compile(r"(MEM_[A-Z_]+):\s*(\d+)")


def build_stats(runs, metrics):
    stats = {}
    for metric in metrics:
        values = [run[metric] for run in runs]
        stats[metric] = {
            "mean_us": round(statistics.mean(values), 2),
            "min_us": min(values),
            "max_us": max(values),
            "stdev_us": round(statistics.pstdev(values), 2),
        }
    return stats


def parse_runs(text, cfg):
    runs = []
    for line in text.splitlines():
        m = cfg["run_re"].search(line)
        if not m:
            continue
        gd = m.groupdict()
        run = {"run": int(gd["run"])}
        if "curve" in gd and gd["curve"]:
            run["curve"] = gd["curve"]
        for metric in cfg["metrics"]:
            run[metric] = int(gd[metric])
        run[cfg["success_field"]] = bool(int(gd[cfg["success_field"]]))
        runs.append(run)
    return runs


def parse_mem(text):
    mem = {}
    for line in text.splitlines():
        m = MEM_RE.search(line)
        if m:
            mem[m.group(1)] = int(m.group(2))
    out = {}
    if "MEM_TA_HEAP_MAX_BYTES" in mem:
        out["ta"] = {
            "heap_max_bytes": mem.get("MEM_TA_HEAP_MAX_BYTES"),
            "heap_pool_bytes": mem.get("MEM_TA_HEAP_POOL_BYTES"),
            "heap_allocated_end_bytes": mem.get("MEM_TA_HEAP_ALLOCATED_BYTES"),
            "alloc_fail": mem.get("MEM_TA_ALLOC_FAIL"),
        }
    if "MEM_CA_VMPEAK_KB" in mem:
        out["ca"] = {
            "vmpeak_kb": mem.get("MEM_CA_VMPEAK_KB"),
            "vmhwm_kb": mem.get("MEM_CA_VMHWM_KB"),
            "vmrss_kb": mem.get("MEM_CA_VMRSS_KB"),
            "vmdata_kb": mem.get("MEM_CA_VMDATA_KB"),
            "vmstk_kb": mem.get("MEM_CA_VMSTK_KB"),
        }
    return out


def parse_meminfo_csv(path):
    """Lee el CSV del sampler de /proc/meminfo y calcula deltas del sistema.

    Formato esperado por fila: timestamp_ms,MemFree,MemAvailable,Buffers,
    Cached,Slab (valores en kB).
    """
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: int(v) for k, v in row.items()})
    if not rows:
        return {}
    free = [r["MemFree"] for r in rows]
    avail = [r["MemAvailable"] for r in rows]
    return {
        "samples": len(rows),
        "mem_free_start_kb": free[0],
        "mem_free_end_kb": free[-1],
        "mem_free_min_kb": min(free),
        "mem_free_peak_drop_kb": free[0] - min(free),
        "mem_available_start_kb": avail[0],
        "mem_available_min_kb": min(avail),
        "mem_available_peak_drop_kb": avail[0] - min(avail),
    }


def parse_artifacts(items):
    artifacts = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Artefacto invalido: {item}")
        name, path = item.split("=", 1)
        p = Path(path)
        if not p.is_file():
            raise ValueError(f"No existe el artefacto {name}: {p}")
        artifacts[name] = {"path": str(p), "bytes": p.stat().st_size}
    return artifacts


def parse_log(algo, text, log_path, meminfo=None, artifacts=None):
    cfg = ALGOS[algo]
    runs = parse_runs(text, cfg)
    if not runs:
        raise ValueError(f"No se encontraron ejecuciones {algo} en el log")

    success_field = cfg["success_field"]
    data = {
        "algorithm": algo,
        "platform": "rpi3",
        "num_runs": len(runs),
        "runs": runs,
        "memory": parse_mem(text),
        "artifact_sizes": artifacts or {},
        "log_path": str(log_path),
    }

    if cfg["curves"]:
        data["by_curve"] = {}
        for curve in cfg["curves"]:
            curve_runs = [r for r in runs if r.get("curve") == curve]
            if not curve_runs:
                continue
            data["by_curve"][curve] = {
                "num_runs": len(curve_runs),
                "stats": build_stats(curve_runs, cfg["metrics"]),
                f"all_{success_field}": all(r[success_field]
                                            for r in curve_runs),
            }
        data[f"all_{success_field}"] = all(r[success_field] for r in runs)
    else:
        data["stats"] = build_stats(runs, cfg["metrics"])
        data[f"all_{success_field}"] = all(r[success_field] for r in runs)

    if meminfo:
        data["system_memory"] = parse_meminfo_csv(meminfo)

    return data


def to_markdown(data):
    algo = data["algorithm"]
    lines = [
        f"# Campaña {algo} sobre OP-TEE / Raspberry Pi 3",
        "",
        f"- Log analizado: `{data['log_path']}`",
        f"- Número de ejecuciones: {data['num_runs']}",
    ]
    for key in data:
        if key.startswith("all_"):
            lines.append(f"- {key}: {'sí' if data[key] else 'no'}")
    lines.append("")

    cfg = ALGOS[algo]
    if cfg["curves"]:
        for curve, block in data.get("by_curve", {}).items():
            lines.append(f"## {curve}")
            lines.append("")
            lines.append("| Métrica | Media (us) | Mín | Máx | Desv. típ. |")
            lines.append("| --- | ---: | ---: | ---: | ---: |")
            for metric in cfg["metrics"]:
                s = block["stats"][metric]
                lines.append(
                    f"| {metric} | {s['mean_us']} | {s['min_us']} | "
                    f"{s['max_us']} | {s['stdev_us']} |")
            lines.append("")
    else:
        lines.append("## Estadística por operación")
        lines.append("")
        lines.append("| Métrica | Media (us) | Mín | Máx | Desv. típ. |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for metric in cfg["metrics"]:
            s = data["stats"][metric]
            lines.append(
                f"| {metric} | {s['mean_us']} | {s['min_us']} | "
                f"{s['max_us']} | {s['stdev_us']} |")
        lines.append("")

    mem = data.get("memory", {})
    if mem:
        lines.append("## Memoria observada")
        lines.append("")
        if "ta" in mem:
            ta = mem["ta"]
            lines.append(
                f"- TA heap: máximo {ta['heap_max_bytes']} B sobre un pool "
                f"de {ta['heap_pool_bytes']} B; "
                f"{ta['heap_allocated_end_bytes']} B vivos al cierre; "
                f"{ta['alloc_fail']} fallos de asignación.")
        if "ca" in mem:
            ca = mem["ca"]
            lines.append(
                f"- CA: VmPeak {ca['vmpeak_kb']} kB, VmHWM {ca['vmhwm_kb']} kB, "
                f"VmRSS {ca['vmrss_kb']} kB, VmData {ca['vmdata_kb']} kB, "
                f"VmStk {ca['vmstk_kb']} kB.")
        lines.append("")

    sysmem = data.get("system_memory", {})
    if sysmem:
        lines.append("## Memoria del sistema durante la campaña")
        lines.append("")
        lines.append(
            f"- MemFree: inicio {sysmem['mem_free_start_kb']} kB, "
            f"mínimo {sysmem['mem_free_min_kb']} kB, "
            f"caída máxima {sysmem['mem_free_peak_drop_kb']} kB "
            f"({sysmem['samples']} muestras).")
        lines.append(
            f"- MemAvailable: inicio {sysmem['mem_available_start_kb']} kB, "
            f"caída máxima {sysmem['mem_available_peak_drop_kb']} kB.")
        lines.append("")

    if data["artifact_sizes"]:
        lines.append("## Tamaños de artefactos")
        lines.append("")
        lines.append("| Artefacto | Bytes | Ruta |")
        lines.append("| --- | ---: | --- |")
        for name, art in data["artifact_sizes"].items():
            lines.append(f"| {name} | {art['bytes']} | `{art['path']}` |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("algo", choices=sorted(ALGOS))
    parser.add_argument("log_path")
    parser.add_argument("--meminfo", help="CSV del sampler de /proc/meminfo")
    parser.add_argument("--markdown", help="Ruta de salida Markdown")
    parser.add_argument("--json", help="Ruta de salida JSON")
    parser.add_argument("--artifact", action="append", default=[],
                        help="nombre=ruta de un artefacto a registrar")
    args = parser.parse_args()

    log_path = Path(args.log_path)
    data = parse_log(
        args.algo,
        log_path.read_text(encoding="utf-8", errors="replace"),
        log_path,
        meminfo=args.meminfo,
        artifacts=parse_artifacts(args.artifact),
    )

    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    if args.markdown:
        Path(args.markdown).write_text(to_markdown(data), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
