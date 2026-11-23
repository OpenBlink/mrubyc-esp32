#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mrbc=$(realpath -- "$1")
compiler_version=$(sed -n 's/^MRUBY_VERSION = "\(.*\)"$/\1/p' "$root/vendor/mrubyc/src/VERSION")
if [[ -z "$compiler_version" ]] || [[ "$("$mrbc" --version)" != "mruby $compiler_version "* ]]; then
  printf 'Expected mruby %s mrbc\n' "$compiler_version" >&2
  exit 1
fi

for script in "$root"/examples/*/*.rb; do
  symbol=$(basename -- "$script" .rb)_bytecode
  "$mrbc" --remove-lv "-B$symbol" -o "$(dirname -- "$script")/main/$symbol.h" "$script"
done
