#!/usr/bin/env python3
import argparse
import json
import tarfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / ".local-deps" / "nist-pqc-dig-sig-round2"
USER_AGENT = "Mozilla/5.0 TFG-PQC-OPTEE/1.0"

CATALOG = {
    "hawk": {
        "algorithm": "HAWK",
        "family": "lattice-based signatures",
        "url": "https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-2/submission-pkg/hawk-submission-round2.zip",
        "priority": 1,
        "status": "implemented_hawk512_qemu",
        "nist_round": 2,
    },
    "mayo": {
        "algorithm": "MAYO",
        "family": "multivariate signatures",
        "url": "https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-2/submission-pkg/mayo-submission-round2.tar.gz",
        "priority": 2,
        "status": "implemented_mayo1_qemu",
        "nist_round": 2,
    },
    "faest": {
        "algorithm": "FAEST",
        "family": "symmetric-based signatures",
        "url": "https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-2/submission-pkg/faest-submission-round2.zip",
        "priority": 3,
        "status": "candidate_after_hawk_mayo",
        "nist_round": 2,
    },
    "snova": {
        "algorithm": "SNOVA",
        "family": "multivariate signatures",
        "url": "https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-2/submission-pkg/snova-submission-round2.zip",
        "priority": 4,
        "status": "reserve",
        "nist_round": 2,
    },
    "uov": {
        "algorithm": "UOV",
        "family": "multivariate signatures",
        "url": "https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-2/submission-pkg/uov-submission-round2.zip",
        "priority": 5,
        "status": "reserve",
        "nist_round": 2,
    },
}


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_file():
        return
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        output.write_bytes(response.read())


def archive_name(name: str, url: str) -> str:
    if url.endswith(".tar.gz"):
        return f"{name}.tar.gz"
    if url.endswith(".tgz"):
        return f"{name}.tgz"
    return f"{name}.zip"


def extract(archive_path: Path, dest: Path) -> None:
    marker = dest / ".extracted"
    if marker.is_file():
        return
    dest.mkdir(parents=True, exist_ok=True)
    if archive_path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(dest)
    else:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(dest)
    marker.write_text("ok\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("algorithms", nargs="*", choices=sorted(CATALOG))
    parser.add_argument("--dest", default=str(DEFAULT_DEST))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    dest = Path(args.dest)
    names = args.algorithms or ["hawk", "mayo", "faest"]
    selected = {name: CATALOG[name] for name in names}
    print(json.dumps(selected, indent=2, sort_keys=True))

    if not args.download and not args.extract:
        return 0

    for name, item in selected.items():
        archive_path = dest / archive_name(name, item["url"])
        download(item["url"], archive_path)
        if args.extract:
            extract(archive_path, dest / name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
