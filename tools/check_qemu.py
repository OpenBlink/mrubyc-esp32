import re
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
    "parity": [
        b"Finally number of registers used was", b"Runtime options verified",
        b"Permanent task bypassed the teardown hook", b"Returned from app_main()",
    ],
    "oom_default": [
        b"Triggering pool exhaustion", b"Fatal error: Out of memory.", b"abort() was called",
    ],
    "oom_stats": [
        b"Triggering pool exhaustion", b"mruby/c pool:", b"Fatal error: Out of memory.",
        b"abort() was called",
    ],
    "exception_default": [
        b"Triggering unhandled exception", b"unhandled test exception",
        b"Scheduler returned the exception status", b"Returned from app_main()",
    ],
    "exception_panic": [
        b"Triggering unhandled exception", b"unhandled test exception", b"abort() was called",
    ],
}

FATAL_PROFILES = {"oom_default", "oom_stats", "exception_panic"}


def main(example, target, root, profile="default"):
    build = Path(root).resolve() / f"{example}-{target}-{profile}"
    project = Path(__file__).resolve().parents[1] / "test_app" if example == "test_app" else build / "example"
    command = ["idf.py", "-C", str(project), "-B", str(build), "qemu"]
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(["timeout", "-k", "5s", "25s", *command], stdout=log, stderr=log)
        log.seek(0)
        output = log.read()
    sys.stdout.buffer.write(output)
    if result.returncode not in (0, 124):
        raise SystemExit(f"QEMU command exited {result.returncode}")
    start = 0
    for marker in EXPECTED[example if profile == "default" else profile]:
        location = output.find(marker, start)
        if location == -1:
            raise SystemExit(f"Missing or out-of-order serial marker: {marker.decode()}")
        start = location + len(marker)
    if b"Guru Meditation Error" in output or (profile not in FATAL_PROFILES and b"abort() was called" in output):
        raise SystemExit("Firmware crashed")
    if profile in FATAL_PROFILES and (
        b"Returned from app_main()" in output or b"Pool exhaustion returned unexpectedly" in output
        or b"Scheduler returned the exception status" in output or b"watchdog got triggered" in output
    ):
        raise SystemExit("Firmware did not halt at the intended abort")
    if profile == "oom_default" and b"mruby/c pool:" in output:
        raise SystemExit("Default OOM unexpectedly printed pool statistics")
    if profile == "oom_stats":
        match = re.search(rb"mruby/c pool: total=(\d+) used=(\d+) free=(\d+) bytes", output)
        if match is None:
            raise SystemExit("Missing pool byte counts")
        total, used, free = map(int, match.groups())
        if total != 32768 or not (0 < used < total and 0 < free <= total - used):
            raise SystemExit("Invalid pool byte counts")


if __name__ == "__main__":
    main(*sys.argv[1:])
