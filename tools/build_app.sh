#!/usr/bin/env bash
set -euo pipefail

project=$1
target=$2
profile=${3:-default}
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
output=${BUILD_OUTPUT_DIR:-"$root/build"}
mkdir -p -- "$output"
output=$(realpath -- "$output")
build="$output/$project-$target-$profile"
args=(-D "SDKCONFIG=$build/sdkconfig" -D "IDF_TARGET=$target")

if [[ "$project" = test_app ]]; then
  source_dir="$root/test_app"
  args+=(-D "SDKCONFIG_DEFAULTS=$source_dir/sdkconfig.ci.$profile")
else
  source_dir="$build/example"
  python "$root/tools/prepare_example.py" "$project" "$source_dir"
fi

rm -f -- "$build/sdkconfig"
idf.py -C "$source_dir" -B "$build" "${args[@]}" build
