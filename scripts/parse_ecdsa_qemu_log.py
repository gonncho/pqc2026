#!/usr/bin/env python3
import argparse
import json
import re
import statistics
from pathlib import Path


METRICS = ("nop_us", "fresh_session_nop_us", "keygen_us", "sign_us", "verify_us")
EXPECTED_CURVES = ("P-256", "P-384")

RUN_RE = re.compile(
    r"Run (?P<curve>P-\d+) (?P<run>\d+): nop=(?P<nop>\d+) us "
    r"fresh_session_nop=(?P<fresh_session_nop>\d+) us "
    r"keygen=(?P<keygen>\d+) us sign=(?P<sign>\d+) us "
    r"verify=(?P<verify>\d+) us verify_ok=(?P<verify_ok>\d+) "
    r"pk=(?P<pk>[0-9a-f.]+)"
)
AVG_RE = re.compile(
    r"Average (?P<curve>P-\d+) "
    r"(?P<name>nop|fresh_session_nop|keygen|sign|verify):\s+"
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
    curves: dict[str, dict] = {}

    for curve in EXPECTED_CURVES:
        curves[curve] = {
            "runs": [],
            "averages": {},
        }

    for line in text.splitlines():
        match = RUN_RE.search(line)
        if match:
            curve = match.group("curve")
            if curve not in curves:
                curves[curve] = {"runs": [], "averages": {}}
            curves[curve]["runs"].append(
                {
                    "run": int(match.group("run")),
                    "nop_us": int(match.group("nop")),
                    "fresh_session_nop_us": int(match.group("fresh_session_nop")),
                    "keygen_us": int(match.group("keygen")),
                    "sign_us": int(match.group("sign")),
                    "verify_us": int(match.group("verify")),
                    "verify_ok": bool(int(match.group("verify_ok"))),
                    "pk_prefix": match.group("pk"),
                }
            )
            continue

        match = AVG_RE.search(line)
        if match:
            curve = match.group("curve")
            if curve not in curves:
                curves[curve] = {"runs": [], "averages": {}}
            curves[curve]["averages"][f"{match.group('name')}_us"] = int(
                match.group("value")
            )

    for curve in EXPECTED_CURVES:
        if not curves[curve]["runs"]:
            raise ValueError(f"No se encontraron ejecuciones ECDSA {curve}")
        if set(curves[curve]["averages"]) != set(METRICS):
            raise ValueError(f"No se encontraron medias completas ECDSA {curve}")
        curves[curve]["stats"] = build_stats(curves[curve]["runs"])
        curves[curve]["all_verify_ok"] = all(
            run["verify_ok"] for run in curves[curve]["runs"]
        )
        curves[curve]["num_runs"] = len(curves[curve]["runs"])

    return {
        "curves": curves,
        "artifact_sizes": artifacts or {},
        "all_verify_ok": all(curves[curve]["all_verify_ok"] for curve in EXPECTED_CURVES),
        "log_path": str(log_path),
    }


def append_curve_markdown(lines: list[str], curve: str, data: dict) -> None:
    labels = {
        "nop_us": "NOP",
        "fresh_session_nop_us": "Fresh session NOP",
        "keygen_us": "Keygen",
        "sign_us": "Sign",
        "verify_us": "Verify",
    }

    lines.extend(
        [
            f"## ECDSA {curve}",
            "",
            f"- Numero de ejecuciones: {data['num_runs']}",
            f"- Verificacion correcta en todas las ejecuciones: "
            f"{'si' if data['all_verify_ok'] else 'no'}",
            "",
            "| Run | NOP (us) | Fresh session NOP (us) | Keygen (us) | Sign (us) | Verify (us) | verify_ok | pk prefix |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )

    for run in data["runs"]:
        lines.append(
            f"| {run['run']} | {run['nop_us']} | "
            f"{run['fresh_session_nop_us']} | {run['keygen_us']} | "
            f"{run['sign_us']} | {run['verify_us']} | "
            f"{int(run['verify_ok'])} | {run['pk_prefix']} |"
        )

    lines.extend(["", "### Medias", ""])
    for metric in METRICS:
        lines.append(f"- {labels[metric]}: {data['averages'][metric]} us")

    lines.extend(["", "### Resumen estadístico", ""])
    for metric in METRICS:
        lines.append(
            f"- {labels[metric]}: min {data['stats'][metric]['min_us']} us, "
            f"max {data['stats'][metric]['max_us']} us, "
            f"desviacion tipica {data['stats'][metric]['stdev_us']} us"
        )
    lines.append("")


def to_markdown(data: dict) -> str:
    lines = [
        "# Resultado automatizado ECDSA sobre OP-TEE/QEMU",
        "",
        f"- Log analizado: `{data['log_path']}`",
        f"- Verificacion correcta global: {'si' if data['all_verify_ok'] else 'no'}",
        "",
    ]

    for curve in EXPECTED_CURVES:
        append_curve_markdown(lines, curve, data["curves"][curve])

    if data["artifact_sizes"]:
        lines.extend(
            [
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
