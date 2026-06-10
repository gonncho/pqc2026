#!/usr/bin/env python3
"""Compara las campañas OP-TEE de QEMU y de Raspberry Pi 3.

Lee optee_qemu_summary_latest.json y optee_rpi3_summary_latest.json, alinea
las operaciones de cada algoritmo y calcula el cociente QEMU/RPi3 (cuántas
veces es la Pi más rápida). Genera:

  - documentacion/resultados/optee_comparison_qemu_rpi3_latest.json
  - documentacion/resultados/optee_comparison_qemu_rpi3_latest.md
  - MemOverleaf-ready: tabla LaTeX en
    documentacion/resultados/tabla_comparativa_qemu_rpi3.tex
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "documentacion" / "resultados"

# Operaciones a comparar y etiqueta legible (clave JSON, etiqueta LaTeX).
OPS = [
    ("nop_us", "NOP"),
    ("fresh_session_nop_us", "Sesión fresca"),
    ("keygen_us", "Keygen"),
    ("sign_us", "Firma"),
    ("verify_us", "Verificación"),
    ("encaps_us", "Encapsulación"),
    ("decaps_us", "Decapsulación"),
]

# Mapa de nombre de campaña QEMU -> (algo rpi3, curva o None).
QEMU_TO_RPI3 = {
    "ML-DSA-65": ("ml_dsa", None),
    "ML-KEM-768": ("ml_kem", None),
    "ECDSA P-256": ("ecdsa", "P-256"),
    "ECDSA P-384": ("ecdsa", "P-384"),
    "HAWK-512": ("hawk", None),
    "MAYO_1": ("mayo", None),
}


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def rpi3_means(rpi3, algo, curve):
    """Devuelve el dict op->media_us de la campaña RPi3 indicada."""
    entry = rpi3["algorithms"].get(algo, {})
    if curve is not None:
        return entry.get("by_curve", {}).get(curve, {})
    return entry.get("means_us", {})


def build_comparison():
    qemu = load("optee_qemu_summary_latest.json")
    rpi3 = load("optee_rpi3_summary_latest.json")

    rows = []
    for camp in qemu["campaigns"]:
        name = camp["campaign"]
        if name not in QEMU_TO_RPI3:
            continue
        algo, curve = QEMU_TO_RPI3[name]
        r_means = rpi3_means(rpi3, algo, curve)
        entry = {
            "campaign": name,
            "family": camp.get("family"),
            "algo": algo,
            "curve": curve,
            "operations": {},
        }
        for key, label in OPS:
            q = camp.get(key)
            r = r_means.get(key)
            if q is None or r is None:
                continue
            ratio = q / r if r else None
            entry["operations"][label] = {
                "qemu_us": round(q, 2),
                "rpi3_us": round(r, 2),
                "speedup_rpi3": round(ratio, 2) if ratio else None,
            }
        rows.append(entry)
    return {"comparison": rows,
            "note": "speedup_rpi3 = tiempo_QEMU / tiempo_RPi3; >1 indica "
                    "que la Pi es más rápida que QEMU para esa operación."}


def comparison_md(data):
    lines = ["# Comparativa OP-TEE: QEMU vs Raspberry Pi 3", "",
             "Cociente `speedup` = tiempo QEMU / tiempo RPi3. Un valor mayor "
             "que 1 indica que el hardware físico es más rápido que el "
             "emulador para esa operación.", ""]
    for row in data["comparison"]:
        lines.append(f"## {row['campaign']}  ({row['family']})")
        lines.append("")
        lines.append("| Operación | QEMU (µs) | RPi3 (µs) | speedup RPi3 |")
        lines.append("| --- | ---: | ---: | ---: |")
        for label, v in row["operations"].items():
            lines.append(
                f"| {label} | {v['qemu_us']:.1f} | {v['rpi3_us']:.1f} | "
                f"{v['speedup_rpi3']:.2f}× |")
        lines.append("")
    return "\n".join(lines)


def comparison_tex(data):
    """Tabla LaTeX lista para incluir en la memoria."""
    lines = [
        "% Tabla generada por scripts/compare_qemu_vs_rpi3.py",
        "\\begin{table}[!htbp]",
        "    \\centering",
        "    \\small",
        "    \\begin{tabular}{llrrr}",
        "        \\toprule",
        "        Campaña & Operación & QEMU (µs) & "
        "RPi3 (µs) & Aceleración \\\\",
        "        \\midrule",
    ]
    for row in data["comparison"]:
        ops = list(row["operations"].items())
        for i, (label, v) in enumerate(ops):
            camp = row["campaign"].replace("_", "\\_") if i == 0 else ""
            lines.append(
                f"        {camp} & {label} & {v['qemu_us']:.0f} & "
                f"{v['rpi3_us']:.0f} & {v['speedup_rpi3']:.2f}$\\times$ \\\\")
        lines.append("        \\midrule")
    lines[-1] = "        \\bottomrule"
    lines += [
        "    \\end{tabular}",
        "    \\caption{Tiempos medios por operación en QEMU y en Raspberry "
        "Pi~3, y aceleración del hardware físico frente al emulador. "
        "La aceleración es el cociente QEMU/RPi3.}",
        "    \\label{tab:comparativa_qemu_rpi3}",
        "\\end{table}",
        "",
    ]
    return "\n".join(lines)


def main():
    data = build_comparison()
    (RESULTS / "optee_comparison_qemu_rpi3_latest.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (RESULTS / "optee_comparison_qemu_rpi3_latest.md").write_text(
        comparison_md(data), encoding="utf-8")
    (RESULTS / "tabla_comparativa_qemu_rpi3.tex").write_text(
        comparison_tex(data), encoding="utf-8")
    print("Comparativa QEMU vs RPi3 escrita en:")
    print(f"  {RESULTS / 'optee_comparison_qemu_rpi3_latest.json'}")
    print(f"  {RESULTS / 'optee_comparison_qemu_rpi3_latest.md'}")
    print(f"  {RESULTS / 'tabla_comparativa_qemu_rpi3.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
