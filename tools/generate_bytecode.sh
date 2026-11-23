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

if "$check"; then
  shopt -s nullglob
  for header in "$root"/examples/*/main/*_bytecode.h "$root"/test_app/main/*_bytecode.h; do
    script="${header%/main/*}/$(basename -- "$header" _bytecode.h).rb"
    if [[ ! -f "$script" ]]; then
      printf 'Orphaned bytecode header: %s (missing %s)\n' "${header#"$root"/}" "${script#"$root"/}" >&2
      exit 1
    fi
  done
fi

for script in "$root"/examples/*/*.rb "$root"/test_app/*.rb; do
  symbol=$(basename -- "$script" .rb)_bytecode
  header="$(dirname -- "$script")/main/$symbol.h"
  if "$check"; then
    "$mrbc" --remove-lv "-B$symbol" -o "$work/$symbol.h" "$script"
    diff -u "$header" "$work/$symbol.h"
  else
    "$mrbc" --remove-lv "-B$symbol" -o "$header" "$script"
  fi
done
