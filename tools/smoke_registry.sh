#!/usr/bin/env bash
set -euo pipefail

version=$1
project=$(mktemp -d)
trap 'rm -rf -- "$project"' EXIT
cp -R examples/hello/. "$project"
printf 'dependencies:\n  openblink/mrubyc-esp32:\n    version: "==%s"\n    registry_url: "https://components-staging.espressif.com"\n' \
  "$version" > "$project/main/idf_component.yml"
idf.py -C "$project" -D IDF_TARGET=esp32 build
