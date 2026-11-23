import sys
import tarfile
from pathlib import PurePosixPath

REQUIRED = {
    "README.md", "LICENSE", "CMakeLists.txt", "Kconfig", "idf_component.yml",
    "vendor/mrubyc/LICENSE", "vendor/mrubyc/LICENSE.unicode",
    "vendor/mrubyc/src/VERSION", "vendor/mrubyc/src/mrblib.c",
    "vendor/mrubyc/hal/esp32/hal.c", "vendor/mrubyc/hal/esp32/hal.h",
}
EXAMPLE_HEADERS = {
    "hello": ("hello_bytecode.h",),
    "vm_tasks": ("first_bytecode.h", "second_bytecode.h"),
    "m5stack": ("hello_display_bytecode.h",),
}


def main(archive):
    with tarfile.open(archive) as package:
        files = {PurePosixPath(member.name).as_posix() for member in package if member.isfile()}
    required = REQUIRED | {
        f"examples/{example}/{path}"
        for example, headers in EXAMPLE_HEADERS.items()
        for path in ("CMakeLists.txt", "main/idf_component.yml", *(f"main/{header}" for header in headers))
    }
    missing = required - files
    excluded = {
        path for path in files
        if path.split("/")[0] in {".git", ".github", "test_app", "tools", "dist"}
        or {"build", "managed_components", "__pycache__"} & set(path.split("/"))
        or PurePosixPath(path).name in {"sdkconfig", "sdkconfig.old", "dependencies.lock"}
    }
    if missing or excluded:
        raise SystemExit(f"Missing: {sorted(missing)}; unexpectedly packaged: {sorted(excluded)}")
    print(f"Registry archive verified: {len(files)} files, three examples, and upstream licenses")


if __name__ == "__main__":
    main(*sys.argv[1:])
