#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "documentacion" / "resultados"
JSON_OUT = RESULTS / "optee_qemu_summary_latest.json"
MD_OUT = RESULTS / "optee_qemu_summary_latest.md"


def load(name: str) -> dict:
    with (RESULTS / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def average_signed_message_bytes(runs: list[dict]) -> int | None:
    values = [run.get("signed_message_bytes") for run in runs]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values))


def row(
    campaign: str,
    family: str,
    source: str,
    data: dict,
    op2: str,
    op3: str,
    op2_label: str,
    op3_label: str,
) -> dict:
    averages = data["averages"]
    stats = data["stats"]
    nop = averages["nop_us"]
    artifact_sizes = data.get("artifact_sizes", {})

    return {
        "campaign": campaign,
        "family": family,
        "source": source,
        "num_runs": data["num_runs"],
        "nop_us": averages["nop_us"],
        "fresh_session_nop_us": averages["fresh_session_nop_us"],
        "fresh_session_over_nop": round(averages["fresh_session_nop_us"] / nop, 2)
        if nop
        else None,
        "keygen_us": averages["keygen_us"],
        op2: averages[op2],
        op3: averages[op3],
        f"{op2}_minus_nop_us": averages[op2] - nop,
        f"{op3}_minus_nop_us": averages[op3] - nop,
        "keygen_min_us": stats["keygen_us"]["min_us"],
        "keygen_max_us": stats["keygen_us"]["max_us"],
        "keygen_stdev_us": stats["keygen_us"]["stdev_us"],
        f"{op2}_min_us": stats[op2]["min_us"],
        f"{op2}_max_us": stats[op2]["max_us"],
        f"{op2}_stdev_us": stats[op2]["stdev_us"],
        f"{op3}_min_us": stats[op3]["min_us"],
        f"{op3}_max_us": stats[op3]["max_us"],
        f"{op3}_stdev_us": stats[op3]["stdev_us"],
        "ca_bytes": artifact_sizes.get("ca", {}).get("bytes"),
        "ta_bytes": artifact_sizes.get("ta", {}).get("bytes"),
        "signed_message_bytes": average_signed_message_bytes(data.get("runs", [])),
        "op2_label": op2_label,
        "op3_label": op3_label,
    }


def build_summary() -> dict:
    dsa = load("optee_ml_dsa_qemu_latest.json")
    kem = load("optee_ml_kem_qemu_latest.json")
    ecdsa = load("optee_ecdsa_qemu_latest.json")
    hawk = load("optee_hawk_qemu_latest.json")
    mayo = load("optee_mayo_qemu_latest.json")
    artifacts = load("optee_artifact_metrics_latest.json")

    campaigns = [
        row(
            "ML-DSA-65",
            "Lattice / FIPS 204",
            "NIST standardized",
            dsa,
            "sign_us",
            "verify_us",
            "Sign",
            "Verify",
        ),
        row(
            "ML-KEM-768",
            "Lattice / FIPS 203",
            "NIST standardized",
            kem,
            "encaps_us",
            "decaps_us",
            "Encaps",
            "Decaps",
        ),
        row(
            "ECDSA P-256",
            "Classical ECC",
            "Classical baseline",
            ecdsa["curves"]["P-256"] | {"artifact_sizes": ecdsa["artifact_sizes"]},
            "sign_us",
            "verify_us",
            "Sign",
            "Verify",
        ),
        row(
            "ECDSA P-384",
            "Classical ECC",
            "Classical baseline",
            ecdsa["curves"]["P-384"] | {"artifact_sizes": ecdsa["artifact_sizes"]},
            "sign_us",
            "verify_us",
            "Sign",
            "Verify",
        ),
        row(
            "HAWK-512",
            "Lattice / NIST additional signatures",
            "Exploratory candidate",
            hawk,
            "sign_us",
            "verify_us",
            "Sign",
            "Verify",
        ),
        row(
            "MAYO_1",
            "Multivariate / NIST additional signatures",
            "Exploratory candidate",
            mayo,
            "sign_us",
            "verify_us",
            "Sign",
            "Verify",
        ),
    ]

    return {
        "platform": "OP-TEE/QEMU ARMv8",
        "num_runs_per_campaign": 20,
        "campaigns": campaigns,
        "artifact_metrics": artifacts["artifact_metrics"],
        "methodological_note": (
            "Times are CA-observed round-trip times in QEMU. Artifact sizes are compiled "
            "binary sizes, not RAM, physical flash, or energy measurements."
        ),
    }


def to_markdown(data: dict) -> str:
    lines = [
        "# Resumen comparativo OP-TEE/QEMU",
        "",
        f"- Plataforma: {data['platform']}",
        f"- Repeticiones por campaña: {data['num_runs_per_campaign']}",
        "- Fuente de verdad: JSON `optee_*_qemu_latest.json` generados por los parsers.",
        "- Nota: los tiempos son round-trip observados desde la CA; los tamaños son artefactos compilados, no RAM, flash real ni consumo.",
        "",
        "## Medias y tamaños",
        "",
        "| Campaña | Familia | NOP | Fresh NOP | Fresh/NOP | Keygen | Op. 2 | Op. 3 | CA bytes | TA bytes | sm bytes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for item in data["campaigns"]:
        sm = item["signed_message_bytes"] if item["signed_message_bytes"] is not None else "N/D"
        lines.append(
            f"| `{item['campaign']}` | {item['family']} | {item['nop_us']} | "
            f"{item['fresh_session_nop_us']} | {item['fresh_session_over_nop']} | "
            f"{item['keygen_us']} | {item.get('sign_us', item.get('encaps_us'))} "
            f"({item['op2_label']}) | {item.get('verify_us', item.get('decaps_us'))} "
            f"({item['op3_label']}) | {item['ca_bytes']} | {item['ta_bytes']} | {sm} |"
        )

    lines.extend(
        [
            "",
            "## Estadística por operación",
            "",
            "| Campaña | Operación | Media | Min | Max | Desv. típica | Media - NOP |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in data["campaigns"]:
        op2 = "sign_us" if "sign_us" in item else "encaps_us"
        op3 = "verify_us" if "verify_us" in item else "decaps_us"
        for metric, label in (("keygen_us", "Keygen"), (op2, item["op2_label"]), (op3, item["op3_label"])):
            stat_prefix = "keygen" if metric == "keygen_us" else metric
            minus = item.get(f"{metric}_minus_nop_us", item[metric] - item["nop_us"])
            lines.append(
                f"| `{item['campaign']}` | {label} | {item[metric]} | "
                f"{item[f'{stat_prefix}_min_us']} | {item[f'{stat_prefix}_max_us']} | "
                f"{item[f'{stat_prefix}_stdev_us']} | {minus} |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    data = build_summary()
    JSON_OUT.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    MD_OUT.write_text(to_markdown(data), encoding="utf-8")
    print(f"summary json written to {JSON_OUT}")
    print(f"summary markdown written to {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
