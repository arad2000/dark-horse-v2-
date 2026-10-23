#!/usr/bin/env bash
set -euo pipefail

# Guard: Block raw Sanjesh capacity/program dump JSON files from public GitHub Pages (docs/).
# Allowed frontend data files (micro_motives.json, questions_v2.json, trait_map_v3.json,
# majors_catalog_ui_v1.json, value_poles_v2.json, school_branches_v2.json, manifest.json, etc.)
# are unaffected. Live capacity data (1405 + record) lives strictly on deploy / server runtime.

check_tree() {
  local root_dir="$1"
  local docs_dir="${root_dir%/}/docs"

  if [[ ! -d "$docs_dir" ]]; then
    echo "[ERROR] Expected docs/ directory not found under: $root_dir" >&2
    return 1
  fi

  local -a found=()
  while IFS= read -r -d '' file; do
    found+=("${file#"${root_dir%/}/"}")
  done < <(
    find "$docs_dir" -type f \( \
      -path "$docs_dir/data/sanjesh_*.json" \
      -o -name "sanjesh_*_programs.json" \
      -o -name "sanjesh_record_capacity_full.json" \
    \) -print0 | sort -z
  )

  if (( ${#found[@]} > 0 )); then
    echo "::error::این فایل‌ها در GitHub Pages مجاز نیستند؛ ظرفیت فقط روی سرور/deploy است." >&2
    echo "[BLOCKED] Forbidden Sanjesh capacity/program dump file(s) detected in public Pages tree (docs/):" >&2
    for item in "${found[@]}"; do
      echo "  - $item" >&2
    done
    echo "این فایل‌ها در GitHub Pages مجاز نیستند؛ ظرفیت فقط روی سرور/deploy است." >&2
    return 1
  fi

  echo "[OK] Public Pages guard passed (${docs_dir}: 0 Sanjesh capacity/program JSON dumps found)."
  return 0
}

run_self_test() {
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '$tmp_dir'" EXIT RETURN

  mkdir -p "$tmp_dir/docs/data"

  # 1) Allowed public frontend JSON/docs files MUST pass
  local -a allowed_files=(
    "docs/data/micro_motives.json"
    "docs/data/questions_v2.json"
    "docs/data/trait_map_v3.json"
    "docs/data/value_poles_v2.json"
    "docs/data/school_branches_v2.json"
    "docs/majors_catalog_ui_v1.json"
    "docs/manifest.json"
    "docs/trait_map_v3.json"
    "docs/SANJESH_ADMISSION_ENGINE_CONTRACT.md"
    "docs/admission_chance_ui.js"
  )
  for rel in "${allowed_files[@]}"; do
    printf '{}\n' > "$tmp_dir/$rel"
  done

  check_tree "$tmp_dir" >/dev/null

  # 2) Forbidden Sanjesh dump patterns MUST fail with clear error message
  local -a forbidden_cases=(
    "docs/data/sanjesh_dummy_1404_programs.json"
    "docs/data/sanjesh_riazi_1405_programs.json"
    "docs/data/sanjesh_record_capacity_full.json"
    "docs/data/sanjesh_any_dump.json"
    "docs/sanjesh_record_capacity_full.json"
  )

  for bad in "${forbidden_cases[@]}"; do
    printf '[]\n' > "$tmp_dir/$bad"
    set +e
    output="$(check_tree "$tmp_dir" 2>&1)"
    rc=$?
    set -e
    rm -f "$tmp_dir/$bad"

    if (( rc == 0 )); then
      echo "[SELF-TEST FAIL] Expected failure for $bad, but exited 0" >&2
      return 1
    fi
    if [[ "$output" != *"$bad"* ]] || [[ "$output" != *"این فایل‌ها در GitHub Pages مجاز نیستند؛ ظرفیت فقط روی سرور/deploy است."* ]]; then
      echo "[SELF-TEST FAIL] Unexpected error output for $bad: $output" >&2
      return 1
    fi
  done

  # Re-verify clean state passes again after removing dummy files
  check_tree "$tmp_dir" >/dev/null
  echo "[OK] Sanjesh Pages guard self-test passed (10 allowed files accepted; ${#forbidden_cases[@]} forbidden patterns rejected)."
}

if [[ "${1:-}" == "--self-test" ]]; then
  run_self_test
else
  check_tree "${1:-.}"
fi
