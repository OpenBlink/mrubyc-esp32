import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "mrubyc/mrubyc"
VERSION = re.compile(r"release(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def gh(*args):
    return subprocess.check_output(["gh", *args])


def version_key(tag):
    match = VERSION.fullmatch(tag)
    if not match:
        raise ValueError(f"Unexpected release tag: {tag!r}")
    return tuple(map(int, match.groups()))


def vendored_version(directory):
    (version,) = re.findall(r'^MRUBYC_VERSION = "([^"]+)"$', (directory / "src/VERSION").read_text(), re.M)
    return version


def bytecode_compatibility(directory):
    compiler = re.search(r'^MRUBY_VERSION = "([^"]+)"$', (directory / "src/VERSION").read_text(), re.M)
    rite = re.search(r'\bRITE_VERSION\s*\[\s*4\s*\]\s*=\s*"([0-9]{4})"', (directory / "src/load.c").read_text())
    if not compiler or not rite:
        raise ValueError("Cannot verify the upstream compiler and RITE version; import manually and regenerate example bytecode.")
    return compiler.group(1), rite.group(1)


def import_latest(release, root):
    tag = release["tag_name"]
    current = root / "vendor/mrubyc"
    if version_key(tag) <= version_key(f"release{vendored_version(current)}"):
        return None

    version = tag.removeprefix("release")
    name = f"mrubyc-{tag}.tar.gz"
    (asset,) = [asset for asset in release["assets"] if asset["name"] == name]
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Missing official SHA-256 digest")

    with TemporaryDirectory(dir=root) as temporary:
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
        if vendored_version(source) != version:
            raise ValueError("Release asset VERSION does not match its tag")

        previous_compiler, previous_rite = bytecode_compatibility(current)
        compiler, rite = bytecode_compatibility(source)
        if (compiler, rite) != (previous_compiler, previous_rite):
            raise ValueError(
                f"Example bytecode must be regenerated: mruby {previous_compiler} (RITE{previous_rite}) "
                f"changes to mruby {compiler} (RITE{rite}). "
                f"Import {tag} manually and run bash tools/generate_bytecode.sh with mruby {compiler}'s mrbc."
            )

        replacement = staging / "vendor"
        shutil.copytree(source / "src", replacement / "src")
        shutil.copytree(source / "hal/esp32", replacement / "hal/esp32")
        for license_name in ("LICENSE", "LICENSE.unicode"):
            shutil.copyfile(source / license_name, replacement / license_name)

        manifest = root / "idf_component.yml"
        updated, count = re.subn(r'^version: "[^"]+"$', f'version: "{version}"', manifest.read_text(), flags=re.M)
        if count != 1:
            raise ValueError("Expected one manifest version")
        shutil.rmtree(current)
        replacement.rename(current)
        manifest.write_text(updated)
    return version


if __name__ == "__main__":
    release = json.loads(gh("api", f"repos/{UPSTREAM}/releases/latest"))
    version = import_latest(release, ROOT)
    if version:
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\n")
