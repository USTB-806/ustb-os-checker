#!/usr/bin/env bash
set -e

EXTRACT_DIR=""
WORK_ROOT=""

json_escape() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])'
  else
    sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n' ' '
  fi
}

emit_json() {
  verdict="$1"
  score="$2"
  comment="$3"
  detail="$4"
  comment_esc="$(printf '%s' "$comment" | json_escape)"
  detail_esc="$(printf '%s' "$detail" | json_escape)"
  printf '{"verdict":"%s","score":%s,"comment":"%s","detail":"%s"}\n' "$verdict" "$score" "$comment_esc" "$detail_esc"
}

collect_debug() {
  submit_dirs="$(for p in /coursegrader/submit /coursegrader/submission /submit; do if [ -d "$p" ]; then printf '%s(yes);' "$p"; else printf '%s(no);' "$p"; fi; done)"
  coursegrader_ls="$(ls -la /coursegrader 2>&1 | tr '\n' ';')"
  grader_vendor_ls="$(ls -la /coursegrader/dockerext/grader_vendor 2>&1 | tr '\n' ';')"
  submit_ls="$( [ -n "$SUBMIT" ] && ls -la "$SUBMIT" 2>&1 | tr '\n' ';' || true )"
  submit_tree="$( [ -n "$SUBMIT" ] && find "$SUBMIT" -maxdepth 3 -mindepth 1 -print 2>&1 | head -n 40 | tr '\n' ';' || true )"
  archive_hint="$(find /coursegrader/submit -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' -o -name '*.tar' \) 2>/dev/null | tr '\n' ';')"
  printf 'pwd=%s;cguserid=%s;chapter=%s;submit_candidates=%s;coursegrader_ls=%s;grader_vendor_ls=%s;submit_ls=%s;submit_tree=%s;submit_archives=%s;effective_submit=%s;extract_dir=%s;work_root=%s' \
    "$(pwd)" "${CGUSERID:-}" "${CHAPTER:-}" "$submit_dirs" "$coursegrader_ls" "$grader_vendor_ls" "$submit_ls" "$submit_tree" "$archive_hint" "$SUBMIT" "$EXTRACT_DIR" "$WORK_ROOT"
}

extract_archive() {
  archive_path="$1"
  out_dir="$2"
  mkdir -p "$out_dir"
  case "$archive_path" in
    *.tar.gz|*.tgz)
      tar -xzf "$archive_path" -C "$out_dir"
      ;;
    *.tar)
      tar -xf "$archive_path" -C "$out_dir"
      ;;
    *.zip)
      if command -v unzip >/dev/null 2>&1; then
        unzip -q "$archive_path" -d "$out_dir"
      else
        return 2
      fi
      ;;
    *)
      return 1
      ;;
  esac
  return 0
}

find_vendor_source_dir() {
  search_root="$1"
  if find "$search_root" -mindepth 1 -maxdepth 2 -name .cargo-checksum.json | grep -q .; then
    printf '%s\n' "$search_root"
    return 0
  fi
  if [ -d "$search_root/vendor" ] && find "$search_root/vendor" -mindepth 1 -maxdepth 2 -name .cargo-checksum.json | grep -q .; then
    printf '%s\n' "$search_root/vendor"
    return 0
  fi
  if [ -d "$search_root/.cargo/vendor" ] && find "$search_root/.cargo/vendor" -mindepth 1 -maxdepth 2 -name .cargo-checksum.json | grep -q .; then
    printf '%s\n' "$search_root/.cargo/vendor"
    return 0
  fi

  found_vendor="$(find "$search_root" -type d -name vendor | while read -r d; do
    if find "$d" -mindepth 1 -maxdepth 2 -name .cargo-checksum.json | grep -q .; then
      printf '%s\n' "$d"
      break
    fi
  done)"
  if [ -n "$found_vendor" ]; then
    printf '%s\n' "$found_vendor"
    return 0
  fi

  return 1
}

vendor_overlap_count() {
  src_vendor="$1"
  dst_vendor="$2"
  overlap=0

  if [ ! -d "$dst_vendor" ]; then
    printf '0\n'
    return 0
  fi

  for crate_dir in "$src_vendor"/*; do
    [ -d "$crate_dir" ] || continue
    crate_name="$(basename "$crate_dir")"
    if [ -d "$dst_vendor/$crate_name" ]; then
      overlap=$((overlap + 1))
    fi
  done

  printf '%s\n' "$overlap"
}

deploy_one_vendor_archive() {
  archive_path="$1"
  extract_dir="$2"
  project_dir="$3"

  rm -rf "$extract_dir"
  mkdir -p "$extract_dir"
  if ! extract_archive "$archive_path" "$extract_dir"; then
    return 11
  fi

  src_vendor="$(find_vendor_source_dir "$extract_dir")" || return 12
  archive_name="$(basename "$archive_path")"
  kernel_target="$project_dir/kernel/.cargo/vendor"
  easy_fs_target="$project_dir/easy-fs-fuse/.cargo/vendor"
  target_vendor=""

  if printf '%s' "$archive_name" | grep -Eqi 'easy-fs-fuse|easyfs'; then
    target_vendor="$easy_fs_target"
  elif printf '%s' "$archive_name" | grep -Eqi 'kernel'; then
    target_vendor="$kernel_target"
  else
    kernel_score="$(vendor_overlap_count "$src_vendor" "$kernel_target")"
    easy_fs_score="$(vendor_overlap_count "$src_vendor" "$easy_fs_target")"
    if [ "$easy_fs_score" -gt "$kernel_score" ]; then
      target_vendor="$easy_fs_target"
    elif [ "$kernel_score" -gt 0 ]; then
      target_vendor="$kernel_target"
    else
      return 13
    fi
  fi

  rm -rf "$target_vendor"
  mkdir -p "$(dirname "$target_vendor")"
  cp -a "$src_vendor" "$target_vendor"
  printf '%s => %s\n' "$archive_name" "$target_vendor"
  return 0
}

deploy_grader_vendor() {
  grader_vendor_dir="/coursegrader/dockerext/grader_vendor"
  if [ ! -d "$grader_vendor_dir" ]; then
    return 0
  fi

  vendor_archives="$(find "$grader_vendor_dir" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' \) | sort)"
  if [ -z "$vendor_archives" ]; then
    emit_json "RE" 0 "grader vendor missing" "grader_vendor exists but no tar.gz/tgz archives found; $(collect_debug)"
    exit 0
  fi

  deploy_log=""
  archive_count=0
  while read -r archive_path; do
    [ -n "$archive_path" ] || continue
    archive_count=$((archive_count + 1))
    extract_dir="$WORK_ROOT/grader_vendor/extract_$archive_count"
    if ! deploy_result="$(deploy_one_vendor_archive "$archive_path" "$extract_dir" "$PROJ_DIR")"; then
      emit_json "RE" 0 "grader vendor deploy failed" "cannot deploy grader vendor archive: $archive_path; $(collect_debug)"
      exit 0
    fi
    deploy_log="${deploy_log}${deploy_result};"
  done <<EOF
$vendor_archives
EOF

  if [ "$archive_count" -eq 0 ]; then
    emit_json "RE" 0 "grader vendor missing" "grader_vendor exists but archive scan returned zero entries; $(collect_debug)"
    exit 0
  fi
}

refresh_vendor_checksums() {
  vendor_dir="$1"
  [ -d "$vendor_dir" ] || return 0

  find "$vendor_dir" -mindepth 2 -maxdepth 2 -name .cargo-checksum.json | while read -r checksum_file; do
    crate_dir="$(dirname "$checksum_file")"
    python3 - "$checksum_file" "$crate_dir" <<'PY'
import hashlib
import json
import os
import sys

checksum_path = sys.argv[1]
crate_dir = sys.argv[2]

with open(checksum_path, "r", encoding="utf-8") as fp:
    data = json.load(fp)

files = {}
for root, _, filenames in os.walk(crate_dir):
    for name in filenames:
        if name == ".cargo-checksum.json":
            continue
        path = os.path.join(root, name)
        rel = os.path.relpath(path, crate_dir).replace(os.sep, "/")
        h = hashlib.sha256()
        with open(path, "rb") as rf:
            for chunk in iter(lambda: rf.read(1024 * 1024), b""):
                h.update(chunk)
        files[rel] = h.hexdigest()

data["files"] = dict(sorted(files.items()))

with open(checksum_path, "w", encoding="utf-8", newline="\n") as fp:
    json.dump(data, fp, sort_keys=True, separators=(",", ":"))
PY
  done
}

refresh_project_vendor_checksums() {
  refresh_vendor_checksums "$PROJ_DIR/kernel/.cargo/vendor"
  refresh_vendor_checksums "$PROJ_DIR/easy-fs-fuse/.cargo/vendor"
}

SUBMIT=""
for p in /coursegrader/submit /coursegrader/submission /submit; do
  if [ -d "$p" ]; then
    SUBMIT="$p"
    break
  fi
done

if [ -z "$SUBMIT" ]; then
  emit_json "RE" 0 "submit mount missing" "cannot find /coursegrader/submit; $(collect_debug)"
  exit 0
fi

# Always use writable workspace (submit/testdata/dockerext may be read-only mounts)
WORK_ROOT="/tmp/cg_workspace_${CGUSERID:-unknown}"
rm -rf "$WORK_ROOT"
mkdir -p "$WORK_ROOT/submit_in" "$WORK_ROOT/submit_out" "$WORK_ROOT/checker_src"

# Copy submit payload to writable area
cp -a "$SUBMIT"/. "$WORK_ROOT/submit_in/" 2>/dev/null || true

# Expand submit package if archive exists, else use copied tree directly
SUBMIT_ARCHIVE="$(find "$WORK_ROOT/submit_in" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' -o -name '*.tar' \) | head -n1)"
if [ -n "$SUBMIT_ARCHIVE" ]; then
  if ! extract_archive "$SUBMIT_ARCHIVE" "$WORK_ROOT/submit_out"; then
    emit_json "RE" 0 "submit extract failed" "cannot extract submit archive: $SUBMIT_ARCHIVE; $(collect_debug)"
    exit 0
  fi
  EXTRACT_DIR="$WORK_ROOT/submit_out"
  SUBMIT="$WORK_ROOT/submit_out"
else
  SUBMIT="$WORK_ROOT/submit_in"
fi

PROJ_DIR=""

if [ -d "$SUBMIT/kernel" ] && [ -d "$SUBMIT/user" ]; then
  PROJ_DIR="$SUBMIT"
fi

if [ -z "$PROJ_DIR" ] && [ -d "$SUBMIT/ustb-os-kernel/kernel" ] && [ -d "$SUBMIT/ustb-os-kernel/user" ]; then
  PROJ_DIR="$SUBMIT/ustb-os-kernel"
fi

if [ -z "$PROJ_DIR" ]; then
  PROJ_DIR="$(find "$SUBMIT" -maxdepth 6 -type d \( -name kernel -o -name user \) -printf "%h\n" | sort | uniq | while read -r d; do [ -d "$d/kernel" ] && [ -d "$d/user" ] && { echo "$d"; break; }; done)"
fi

if [ -z "$PROJ_DIR" ]; then
  emit_json "RE" 0 "project root not found" "expect kernel/ and user/ in submit; $(collect_debug)"
  exit 0
fi

deploy_grader_vendor
refresh_project_vendor_checksums

# Resolve checker source (dockerext > testdata), but copy/extract into writable workspace first
if [ -d /coursegrader/dockerext/ustb-os-checker ]; then
  cp -a /coursegrader/dockerext/ustb-os-checker "$WORK_ROOT/checker_src/"
elif [ -f /coursegrader/dockerext/dockerext-ustb-os-checker.tar.gz ]; then
  extract_archive /coursegrader/dockerext/dockerext-ustb-os-checker.tar.gz "$WORK_ROOT/checker_src" || true
elif [ -d /coursegrader/testdata/ustb-os-checker ]; then
  cp -a /coursegrader/testdata/ustb-os-checker "$WORK_ROOT/checker_src/"
elif [ -f /coursegrader/testdata/ustb-os-checker-testdata.tar.gz ]; then
  extract_archive /coursegrader/testdata/ustb-os-checker-testdata.tar.gz "$WORK_ROOT/checker_src" || true
elif ls /coursegrader/testdata/*.tar.gz >/dev/null 2>&1; then
  TAR_FILE="$(ls /coursegrader/testdata/*.tar.gz | head -n1)"
  extract_archive "$TAR_FILE" "$WORK_ROOT/checker_src" || true
else
  dockerext_ls="$(ls -la /coursegrader/dockerext 2>&1 | tr '\n' ';')"
  testdata_ls="$(ls -la /coursegrader/testdata 2>&1 | tr '\n' ';')"
  emit_json "RE" 0 "checker not found" "need ustb-os-checker in dockerext or testdata; dockerext_ls=${dockerext_ls}; testdata_ls=${testdata_ls}; $(collect_debug)"
  exit 0
fi

CHECKER_SRC_DIR=""
if [ -d "$WORK_ROOT/checker_src/ustb-os-checker" ]; then
  CHECKER_SRC_DIR="$WORK_ROOT/checker_src/ustb-os-checker"
elif [ -d "$WORK_ROOT/checker_src" ] && [ -f "$WORK_ROOT/checker_src/judge.py" ]; then
  CHECKER_SRC_DIR="$WORK_ROOT/checker_src"
fi

if [ -z "$CHECKER_SRC_DIR" ]; then
  checker_tree="$(find "$WORK_ROOT/checker_src" -maxdepth 3 -mindepth 1 -print 2>&1 | head -n 40 | tr '\n' ';')"
  emit_json "RE" 0 "checker extract failed" "cannot locate checker directory in workspace; checker_tree=${checker_tree}; $(collect_debug)"
  exit 0
fi

rm -rf "$PROJ_DIR/ustb-os-checker"
cp -a "$CHECKER_SRC_DIR" "$PROJ_DIR/ustb-os-checker"

if [ ! -d "$PROJ_DIR/ustb-os-checker" ]; then
  proj_ls="$(ls -la "$PROJ_DIR" 2>&1 | tr '\n' ';')"
  emit_json "RE" 0 "checker deploy failed" "ustb-os-checker directory missing after deploy; proj_ls=${proj_ls}; $(collect_debug)"
  exit 0
fi

cd "$PROJ_DIR/ustb-os-checker"
python3 judge.py --chapter "${CHAPTER:-3}"
