#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "documentacion" / "resultados"


def load(name: str) -> dict:
    with (RESULTS / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    sig_metrics = {"nop_us", "fresh_session_nop_us", "keygen_us", "sign_us", "verify_us"}
    kem_metrics = {"nop_us", "fresh_session_nop_us", "keygen_us", "encaps_us", "decaps_us"}

    dsa = load("optee_ml_dsa_qemu_latest.json")
    kem = load("optee_ml_kem_qemu_latest.json")
    ecdsa = load("optee_ecdsa_qemu_latest.json")
    hawk = load("optee_hawk_qemu_latest.json")
    mayo = load("optee_mayo_qemu_latest.json")

    require(dsa["num_runs"] == 20, f"ML-DSA num_runs={dsa['num_runs']}")
    require(dsa["all_verify_ok"], "ML-DSA all_verify_ok=false")
    require(sig_metrics <= set(dsa["averages"]), "ML-DSA missing metrics")

    require(kem["num_runs"] == 20, f"ML-KEM num_runs={kem['num_runs']}")
    require(kem["all_shared_secret_ok"], "ML-KEM all_shared_secret_ok=false")
    require(kem_metrics <= set(kem["averages"]), "ML-KEM missing metrics")

    require(ecdsa["all_verify_ok"], "ECDSA all_verify_ok=false")
    for curve in ("P-256", "P-384"):
        c = ecdsa["curves"][curve]
        require(c["num_runs"] == 20, f"ECDSA {curve} num_runs={c['num_runs']}")
        require(c["all_verify_ok"], f"ECDSA {curve} all_verify_ok=false")
        require(sig_metrics <= set(c["averages"]), f"ECDSA {curve} missing metrics")

    require(hawk["num_runs"] == 20, f"HAWK num_runs={hawk['num_runs']}")
    require(hawk["all_verify_ok"], "HAWK all_verify_ok=false")
    require(sig_metrics <= set(hawk["averages"]), "HAWK missing metrics")

    require(mayo["num_runs"] == 20, f"MAYO num_runs={mayo['num_runs']}")
    require(mayo["all_verify_ok"], "MAYO all_verify_ok=false")
    require(sig_metrics <= set(mayo["averages"]), "MAYO missing metrics")

    rows = [
        ("ML-DSA-65", dsa["averages"], "sign_us", "verify_us"),
        ("ML-KEM-768", kem["averages"], "encaps_us", "decaps_us"),
        ("ECDSA P-256", ecdsa["curves"]["P-256"]["averages"], "sign_us", "verify_us"),
        ("ECDSA P-384", ecdsa["curves"]["P-384"]["averages"], "sign_us", "verify_us"),
        ("HAWK-512", hawk["averages"], "sign_us", "verify_us"),
        ("MAYO_1", mayo["averages"], "sign_us", "verify_us"),
    ]

    print("validated latest JSON files")
    print()
    print(f"{'Campana':14s} {'NOP':>8s} {'Fresh NOP':>10s} {'Keygen':>10s} {'Sign/Enc':>10s} {'Ver/Dec':>10s}")
    print("-" * 68)
    for name, avg, op2, op3 in rows:
        print(
            f"{name:14s} {avg['nop_us']:8d} {avg['fresh_session_nop_us']:10d} "
            f"{avg['keygen_us']:10d} {avg[op2]:10d} {avg[op3]:10d}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
