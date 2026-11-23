import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY = "  openblink/mrubyc-esp32:"


def main(name, destination):
    if name not in ("hello", "vm_tasks", "m5stack"):
        raise ValueError(f"Unknown example: {name}")
    destination = Path(destination)
    shutil.copytree(
        ROOT / "examples" / name,
        destination,
        ignore=shutil.ignore_patterns("build", "sdkconfig", "sdkconfig.old", "dependencies.lock", "managed_components"),
        dirs_exist_ok=True,
    )
    manifest = destination / "main/idf_component.yml"
    lines = manifest.read_text().splitlines()
    (index,) = [i for i, line in enumerate(lines) if line.startswith(DEPENDENCY)]
    lines[index:index + 1] = [DEPENDENCY, f"    override_path: {json.dumps(str(ROOT))}"]
    manifest.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
