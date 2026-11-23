#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
check=false
if [[ ${1:-} == --check ]]; then
  check=true
  shift
  work=$(mktemp -d)
  trap 'rm -rf "$work"' EXIT
fi
mrbc=$(realpath -- "${1:?Usage: generate_bytecode.sh [--check] MRBC}")
compiler_version=$(sed -n 's/^MRUBY_VERSION = "\(.*\)"$/\1/p' "$root/vendor/mrubyc/src/VERSION")
if [[ -z "$compiler_version" ]] || [[ "$("$mrbc" --version)" != "mruby $compiler_version "* ]]; then
  printf 'Expected mruby %s mrbc\n' "$compiler_version" >&2
  exit 1
fi

for script in "$root"/examples/*/*.rb; do
  symbol=$(basename -- "$script" .rb)_bytecode
  header="$(dirname -- "$script")/main/$symbol.h"
  if "$check"; then
    "$mrbc" --remove-lv "-B$symbol" -o "$work/$symbol.h" "$script"
    diff -u "$header" "$work/$symbol.h"
  else
    "$mrbc" --remove-lv "-B$symbol" -o "$header" "$script"
  fi
done
