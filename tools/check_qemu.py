import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED = {
    "hello": [b"Hello from mruby/c", b"Timer wakeup complete", b"mruby/c scheduler finished"],
    "vm_tasks": [
        b"first: start", b"second: start", b"second: done", b"first: done",
        b"Both mruby/c tasks finished",
    ],
}


def main(example, target, root):
    build = Path(root).resolve() / f"{example}-{target}-default"
    command = ["idf.py", "-C", str(build / "example"), "-B", str(build), "qemu"]
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(["timeout", "-k", "5s", "25s", *command], stdout=log, stderr=log)
        log.seek(0)
        output = log.read()
    sys.stdout.buffer.write(output)
    if result.returncode not in (0, 124):
        raise SystemExit(f"QEMU command exited {result.returncode}")
    start = 0
    for marker in EXPECTED[example]:
        location = output.find(marker, start)
        if location == -1:
            raise SystemExit(f"Missing or out-of-order serial marker: {marker.decode()}")
        start = location + len(marker)
    if b"Guru Meditation Error" in output or b"abort() was called" in output:
        raise SystemExit("Firmware crashed")


if __name__ == "__main__":
    main(*sys.argv[1:])
