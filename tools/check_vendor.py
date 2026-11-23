"""Verify vendor/mrubyc matches the official upstream release asset.

Reads MRUBYC_VERSION from vendor/mrubyc/src/VERSION, downloads the matching
mrubyc/mrubyc release asset after checking its official SHA-256 digest, and
fails when the vendored files differ from the archive or contain extras.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from import_upstream import ROOT, UPSTREAM, gh, vendored_version

VENDORED = ("src", "hal/esp32", "LICENSE", "LICENSE.unicode")


def differences(expected, actual):
    result = subprocess.run(
        ["diff", "--recursive", "--no-dereference", str(expected), str(actual)],
        capture_output=True,
        text=True,
    )
    if result.returncode > 1:
        raise ValueError(result.stderr)
    return result.stdout


def main():
    vendor = ROOT / "vendor/mrubyc"
    version = vendored_version(vendor)
    tag = f"release{version}"
    release = json.loads(gh("api", f"repos/{UPSTREAM}/releases/tags/{tag}"))
    name = f"mrubyc-{tag}.tar.gz"
    (asset,) = [asset for asset in release["assets"] if asset["name"] == name]
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Missing official SHA-256 digest")

    problems = []
    with TemporaryDirectory(dir=ROOT) as temporary:
        staging = Path(temporary)
        archive = staging / name
        subprocess.run(
            ["gh", "release", "download", tag, "--repo", UPSTREAM, "--pattern", name, "--output", str(archive)],
            check=True,
        )
        with archive.open("rb") as data:
            if "sha256:" + hashlib.file_digest(data, "sha256").hexdigest() != digest:
                raise ValueError("Release asset SHA-256 mismatch")
        with tarfile.open(archive) as contents:
            contents.extractall(staging, filter="data")
        source = staging / f"mrubyc-{tag}"

        expected = staging / "expected"
        (expected / "hal").mkdir(parents=True)
        shutil.copytree(source / "src", expected / "src")
        shutil.copytree(source / "hal/esp32", expected / "hal/esp32")
        for license_name in ("LICENSE", "LICENSE.unicode"):
            shutil.copyfile(source / license_name, expected / license_name)

        diff = differences(expected, vendor)
        if diff:
            problems.append(f"vendor/mrubyc differs from {tag}:\n{diff}")

    manifest = re.search(
        r'^version: "([^"]+)"$', (ROOT / "idf_component.yml").read_text(), re.M
    )
    manifest_version = manifest.group(1) if manifest else None
    # A packaging revision (3.4.1~1) re-publishes the same upstream release.
    if manifest_version is None or manifest_version.split("~", 1)[0] != version:
        problems.append(
            f"idf_component.yml version {manifest_version!r} "
            f"does not match vendored MRUBYC_VERSION {version!r}"
        )

    if problems:
        print("\n\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print(f"vendor/mrubyc verified: identical to {tag} ({', '.join(VENDORED)})")
    print(f"idf_component.yml version verified: {version}")


if __name__ == "__main__":
    main()
