#!/usr/bin/env bash
# Builds one matrix group from detect_recipe_matrix.py: a JSON list of targets
# ({"name", "version", "path", "reference"}) ordered dependencies first.
#
#   build_recipe_group.sh [--upload <remote>] '<targets JSON>'
#
# Every recipe of the group is exported before anything is built, so a recipe can
# require one that is added in the same change and is on no remote yet; the
# dependency is then built once, reused from the local cache by the recipes after it.
set -euo pipefail

upload_remote=""
if [[ "${1:-}" == "--upload" ]]; then
  upload_remote="$2"
  shift 2
fi
targets_json="$1"

mapfile -t targets < <(jq -c '.[]' <<<"$targets_json")
if [[ ${#targets[@]} -eq 0 ]]; then
  echo "No targets in group" >&2
  exit 1
fi

for target in "${targets[@]}"; do
  conan export "$(jq -r .path <<<"$target")" --version="$(jq -r .version <<<"$target")"
done

for target in "${targets[@]}"; do
  path="$(jq -r .path <<<"$target")"
  version="$(jq -r .version <<<"$target")"
  reference="$(jq -r .reference <<<"$target")"

  # Optional per-recipe flags for CI-only builds (e.g. restricting the module set).
  extra_args=()
  if [[ -f "$path/../ci-args" ]]; then
    mapfile -t extra_args < <(grep -v "^\s*#" "$path/../ci-args" | sed "/^\s*$/d")
  fi

  echo "::group::conan create $reference"
  conan create "$path" --version="$version" --build=missing "${extra_args[@]}"
  echo "::endgroup::"

  if [[ -n "$upload_remote" ]]; then
    conan upload "$reference" -r "$upload_remote" --confirm
  fi
done
