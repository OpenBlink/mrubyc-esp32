import argparse
import tarfile
from pathlib import PurePosixPath

REQUIRED = {
    "README.md", "LICENSE", "CMakeLists.txt", "Kconfig", "idf_component.yml", "gptimer_compat.c",
    "vendor/mrubyc/LICENSE", "vendor/mrubyc/LICENSE.unicode",
    "vendor/mrubyc/src/VERSION", "vendor/mrubyc/src/mrblib.c",
    "vendor/mrubyc/hal/esp32/hal.c", "vendor/mrubyc/hal/esp32/hal.h",
}
EXAMPLE_HEADERS = {
    "hello": ("hello_bytecode.h",),
    "vm_tasks": ("first_bytecode.h", "second_bytecode.h"),
    "m5stack": ("hello_display_bytecode.h",),
}


def main(archive, commit_sha=None):
    with tarfile.open(archive) as package:
        files = {PurePosixPath(member.name).as_posix(): member for member in package if member.isfile()}
        if commit_sha:
            from ruamel.yaml import YAML

            with package.extractfile(files["idf_component.yml"]) as manifest_file:
                manifest = YAML(typ="safe").load(manifest_file)
            if manifest.get("repository_info", {}).get("commit_sha") != commit_sha:
                raise SystemExit("Registry archive commit SHA does not match the tagged commit")
    required = REQUIRED | {
        f"examples/{example}/{path}"
        for example, headers in EXAMPLE_HEADERS.items()
        for path in ("CMakeLists.txt", "main/idf_component.yml", *(f"main/{header}" for header in headers))
    }
    missing = required - files.keys()
    excluded = {
        path for path in files
        if path.split("/")[0] in {".git", ".github", "test_app", "tools", "dist"}
        or {"build", "managed_components", "__pycache__"} & set(path.split("/"))
        or PurePosixPath(path).name in {"sdkconfig", "sdkconfig.old", "dependencies.lock"}
    }
    if missing or excluded:
        raise SystemExit(f"Missing: {sorted(missing)}; unexpectedly packaged: {sorted(excluded)}")
    print(f"Registry archive verified: {len(files)} files, three examples, and upstream licenses")
    if commit_sha:
        print(f"Registry archive commit SHA verified: {commit_sha}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit-sha")
    parser.add_argument("archive")
    args = parser.parse_args()
    main(args.archive, args.commit_sha)
