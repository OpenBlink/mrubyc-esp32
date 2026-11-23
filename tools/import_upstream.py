import argparse
import hashlib
import filecmp
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "release3.4.1"
SHA256 = "6e039f3e4ad046c588fbb635cfbe6627ebff8f26cd39ffb32574ca6ef5b6ac46"
ASSET = f"mrubyc-{RELEASE}.tar.gz"
URL = f"https://github.com/mrubyc/mrubyc/releases/download/{RELEASE}/{ASSET}"
SRC_METADATA = {"Makefile", "UnicodeData.txt", "VERSION", "hal_selector.mk"}
MANIFEST_VERSION = re.compile(r'^version: "([0-9]+\.[0-9]+\.[0-9]+)(?:~[0-9]+)?"$', re.M)


def vendored_version(directory):
    (version,) = re.findall(r'^MRUBYC_VERSION = "([^"]+)"$', (directory / "src/VERSION").read_text(), re.M)
    return version


def bytecode_compatibility(directory):
    compiler = re.search(r'^MRUBY_VERSION = "([^"]+)"$', (directory / "src/VERSION").read_text(), re.M)
    rite = re.search(r'\bRITE_VERSION\s*\[\s*4\s*\]\s*=\s*"([0-9]{4})"', (directory / "src/load.c").read_text())
    if not compiler or not rite:
        raise ValueError("Cannot verify the upstream compiler and RITE version; import manually and regenerate example bytecode.")
    return compiler.group(1), rite.group(1)


def snapshot(directory):
    entries = {}
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"Unexpected entry type: {relative}")
        entries[relative] = None if path.is_dir() else path
    return entries


def compare_vendor(expected, current):
    if current.is_symlink() or not current.is_dir():
        raise ValueError("Missing or invalid vendor/mrubyc directory")
    expected_entries = snapshot(expected)
    current_entries = snapshot(current)
    for path in sorted(expected_entries.keys() | current_entries.keys()):
        if path not in current_entries:
            raise ValueError(f"Missing vendored entry: {path}")
        if path not in expected_entries:
            raise ValueError(f"Unexpected vendored entry: {path}")
        source, vendored = expected_entries[path], current_entries[path]
        if (source is None) != (vendored is None) or (
            source is not None and not filecmp.cmp(source, vendored, shallow=False)
        ):
            raise ValueError(f"Vendored entry differs from {RELEASE}: {path}")


def check_build_sources(expected, root):
    makefile = (expected / "src/Makefile").read_text().replace("\\\n", "")
    source_lists = re.findall(r"^[ \t]*SRCS[ \t]*=[ \t]*([^#\n]+)", makefile, re.M)
    if len(source_lists) != 1:
        raise ValueError("Expected one SRCS assignment in the upstream Makefile")
    upstream_sources = sorted(source_lists[0].split())

    cmake = re.sub(r"#[^\n]*", "", (root / "CMakeLists.txt").read_text())
    registrations = re.findall(r"\bidf_component_register\s*\(([^()]*)\)", cmake)
    expected_root = 'set(mrubyc_dir "${CMAKE_CURRENT_LIST_DIR}/vendor/mrubyc")'
    source_dirs = {'"${mrubyc_dir}/src"', '"${mrubyc_dir}/hal/esp32"'}
    if len(registrations) != 1 or expected_root not in cmake:
        raise ValueError("Expected ESP-IDF registration of the bundled mruby/c library")
    args = registrations[0].split()
    if args[:1] != ["SRC_DIRS"] or set(args[1:3]) != source_dirs or args[3:4] != ["INCLUDE_DIRS"] or (
        {"SRCS", "EXCLUDE_SRCS", "SRC_DIRS"} & set(args[3:])
    ):
        raise ValueError("CMakeLists.txt must compile the bundled src and ESP32 HAL directories without source overrides")

    cmake_sources = sorted(
        path.name
        for directory in ("src", "hal/esp32")
        for path in (expected / directory).iterdir()
        if path.is_file() and path.suffix in {".c", ".cpp", ".S"}
    )
    if cmake_sources != upstream_sources:
        raise ValueError("CMakeLists.txt source directories are out of sync with upstream Makefile SRCS:\n"
                         f"  upstream: {' '.join(upstream_sources)}\n  ESP-IDF:  {' '.join(cmake_sources)}")


def stage_vendor(staging, archive):
    if archive is None:
        archive = staging / ASSET
        subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3",
             URL, "--output", str(archive)], check=True,
        )
    with archive.open("rb") as data:
        if hashlib.file_digest(data, "sha256").hexdigest() != SHA256:
            raise ValueError("Release asset SHA-256 mismatch")
    with tarfile.open(archive) as contents:
        contents.extractall(staging, filter="data")
    source = staging / f"mrubyc-{RELEASE}"
    if vendored_version(source) != RELEASE.removeprefix("release"):
        raise ValueError("Release asset VERSION does not match its tag")
    unexpected = sorted(
        path.name for path in (source / "src").iterdir()
        if not path.is_file() or path.is_symlink()
        or (path.suffix not in {".c", ".h"} and path.name not in SRC_METADATA)
    )
    if unexpected:
        raise ValueError(f"Unexpected upstream src entries; review before importing: {', '.join(unexpected)}")

    snapshot(source / "hal/esp32")
    replacement = staging / "vendor"
    shutil.copytree(source / "src", replacement / "src")
    shutil.copytree(source / "hal/esp32", replacement / "hal/esp32")
    for license_name in ("LICENSE", "LICENSE.unicode"):
        shutil.copyfile(source / license_name, replacement / license_name)
    return replacement


def run(mode, archive, root):
    current = root / "vendor/mrubyc"
    manifest = root / "idf_component.yml"
    manifest_text = manifest.read_text()
    versions = MANIFEST_VERSION.findall(manifest_text)
    if len(versions) != 1:
        raise ValueError("Expected one manifest version")
    version = RELEASE.removeprefix("release")
    with TemporaryDirectory(dir=current.parent if mode == "import" else None) as temporary:
        staging = Path(temporary)
        replacement = stage_vendor(staging, archive)
        if mode == "check":
            compare_vendor(replacement, current)
            check_build_sources(replacement, root)
            if versions[0] != version:
                raise ValueError(f"idf_component.yml version {versions[0]} does not match {RELEASE}")
            print(f"Verified vendor/mrubyc, CMake sources and idf_component.yml against {RELEASE}")
            return

        previous_compiler, previous_rite = bytecode_compatibility(current)
        compiler, rite = bytecode_compatibility(replacement)
        if (compiler, rite) != (previous_compiler, previous_rite):
            raise ValueError(
                f"Example bytecode must be regenerated: mruby {previous_compiler} (RITE{previous_rite}) "
                f"changes to mruby {compiler} (RITE{rite}). "
                f"Import {RELEASE} manually and run bash tools/generate_bytecode.sh with mruby {compiler}'s mrbc."
            )

        shutil.rmtree(current)
        replacement.rename(current)
        if versions[0] != version:
            manifest.write_text(MANIFEST_VERSION.sub(f'version: "{version}"', manifest_text))
    print(f"Imported {RELEASE}; review the diff before committing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check or import the pinned mruby/c release asset.")
    parser.add_argument("mode", choices=("check", "import"))
    parser.add_argument("--archive", type=Path, help="use a local copy of the release asset")
    args = parser.parse_args()
    try:
        run(args.mode, args.archive, ROOT)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f"error: {error}\n")
