#!/usr/bin/env python3
import argparse
import json
import re
import statistics
from pathlib import Path


METRICS = ("nop_us", "fresh_session_nop_us", "keygen_us", "encaps_us", "decaps_us")

RUN_RE = re.compile(
    r"Run (?P<run>\d+): nop=(?P<nop>\d+) us "
    r"fresh_session_nop=(?P<fresh_session_nop>\d+) us "
    r"keygen=(?P<keygen>\d+) us "
    r"encaps=(?P<encaps>\d+) us decaps=(?P<decaps>\d+) us "
    r"shared_secret_ok=(?P<shared_secret_ok>\d+) ct=(?P<ct>[0-9a-f.]+)"
)
AVG_RE = re.compile(
    r"Average (?P<name>nop|fresh_session_nop|keygen|encaps|decaps):\s+"
    r"(?P<value>\d+) us"
)


def build_stats(runs: list[dict]) -> dict:
    stats = {}

    for metric in METRICS:
        values = [run[metric] for run in runs]
        stats[metric] = {
            "min_us": min(values),
            "max_us": max(values),
            "stdev_us": round(statistics.pstdev(values), 2),
        }

    return stats


def parse_artifacts(items: list[str]) -> dict:
    artifacts = {}

    for item in items:
        if "=" not in item:
            raise ValueError(f"Artefacto invalido: {item}")
        name, path = item.split("=", 1)
        artifact_path = Path(path)
        if not artifact_path.is_file():
            raise ValueError(f"No existe el artefacto {name}: {artifact_path}")
        artifacts[name] = {
            "path": str(artifact_path),
            "bytes": artifact_path.stat().st_size,
        }

    return artifacts


def parse_log(text: str, log_path: Path, artifacts: dict | None = None) -> dict:
    runs = []
    averages = {}

    for line in text.splitlines():
        match = RUN_RE.search(line)
        if match:
            runs.append(
                {
                    "run": int(match.group("run")),
                    "nop_us": int(match.group("nop")),
                    "fresh_session_nop_us": int(match.group("fresh_session_nop")),
                    "keygen_us": int(match.group("keygen")),
                    "encaps_us": int(match.group("encaps")),
                    "decaps_us": int(match.group("decaps")),
                    "shared_secret_ok": bool(int(match.group("shared_secret_ok"))),
                    "ct_prefix": match.group("ct"),
                }
            )
            continue

        match = AVG_RE.search(line)
        if match:
            averages[f"{match.group('name')}_us"] = int(match.group("value"))

    if not runs:
        raise ValueError("No se encontraron ejecuciones ML-KEM en el log")

    if set(averages) != set(METRICS):
        raise ValueError("No se encontraron las medias completas en el log")

    return {
        "runs": runs,
        "averages": averages,
        "stats": build_stats(runs),
        "artifact_sizes": artifacts or {},
        "all_shared_secret_ok": all(run["shared_secret_ok"] for run in runs),
        "num_runs": len(runs),
        "log_path": str(log_path),
    }


def to_markdown(data: dict) -> str:
    lines = [
        "# Resultado automatizado ML-KEM sobre OP-TEE/QEMU",
        "",
        f"- Log analizado: `{data['log_path']}`",
        f"- Numero de ejecuciones: {data['num_runs']}",
        f"- Secreto compartido correcto en todas las ejecuciones: "
        f"{'si' if data['all_shared_secret_ok'] else 'no'}",
        "",
        "| Run | NOP (us) | Fresh session NOP (us) | Keygen (us) | Encaps (us) | Decaps (us) | shared_secret_ok | ct prefix |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    for run in data["runs"]:
        lines.append(
            f"| {run['run']} | {run['nop_us']} | "
            f"{run['fresh_session_nop_us']} | {run['keygen_us']} | "
            f"{run['encaps_us']} | {run['decaps_us']} | "
            f"{int(run['shared_secret_ok'])} | {run['ct_prefix']} |"
        )

    lines.extend(
        [
            "",
            "## Medias",
            "",
            f"- NOP: {data['averages']['nop_us']} us",
            f"- Fresh session NOP: {data['averages']['fresh_session_nop_us']} us",
            f"- Keygen: {data['averages']['keygen_us']} us",
            f"- Encaps: {data['averages']['encaps_us']} us",
            f"- Decaps: {data['averages']['decaps_us']} us",
            "",
            "## Resumen estadístico",
            "",
        ]
    )

    labels = {
        "nop_us": "NOP",
        "fresh_session_nop_us": "Fresh session NOP",
        "keygen_us": "Keygen",
        "encaps_us": "Encaps",
        "decaps_us": "Decaps",
    }
    for metric in METRICS:
        lines.append(
            f"- {labels[metric]}: min {data['stats'][metric]['min_us']} us, "
            f"max {data['stats'][metric]['max_us']} us, "
            f"desviacion tipica {data['stats'][metric]['stdev_us']} us"
        )

    if data["artifact_sizes"]:
        lines.extend(
            [
                "",
                "## Tamaños de artefactos",
                "",
                "Estos valores son tamaños de artefactos compilados; no son medidas de RAM ni de flash real en hardware.",
                "",
                "| Artefacto | Bytes | Ruta |",
                "| --- | ---: | --- |",
            ]
        )
        for name, artifact in data["artifact_sizes"].items():
            lines.append(
                f"| {name} | {artifact['bytes']} | `{artifact['path']}` |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path")
    parser.add_argument("--markdown")
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()

    log_path = Path(args.log_path)
    artifacts = parse_artifacts(args.artifact)
    data = parse_log(
        log_path.read_text(encoding="utf-8", errors="replace"),
        log_path,
        artifacts,
    )
    print(json.dumps(data, indent=2, sort_keys=True))

    if args.markdown:
        md_path = Path(args.markdown)
        md_path.write_text(to_markdown(data), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
