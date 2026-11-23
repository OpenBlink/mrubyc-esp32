#!/usr/bin/env bash
set -euo pipefail

mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/dist"
tools_dir=${IDF_TOOLS_PATH:-$HOME/.espressif}
if [[ ! -e "$tools_dir/dist" ]]; then
  ln -s "${XDG_CACHE_HOME:-$HOME/.cache}/dist" "$tools_dir/dist"
fi
python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa qemu-riscv32
# export.sh is not compatible with nounset in all IDF versions.
set +u
source "$IDF_PATH/export.sh"
set -u

for target in esp32 esp32c3 esp32s3 esp32c6; do
  bash tools/build_app.sh test_app "$target"
done
for profile in all_options int64 no_timer alloc_libc unicode tick_2_ms tick_4_ms; do
  bash tools/build_app.sh test_app esp32 "$profile"
done
for example in hello vm_tasks; do
  for target in esp32 esp32c3; do
    bash tools/build_app.sh "$example" "$target"
    python tools/check_qemu.py "$example" "$target" "${BUILD_OUTPUT_DIR:-build}"
  done
done
bash tools/build_app.sh m5stack esp32s3
