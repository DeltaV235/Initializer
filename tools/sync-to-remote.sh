#!/usr/bin/env bash
set -euo pipefail

# Sync the entire project to the remote server using rsync.
# Defaults:
#   - Remote: root@192.168.0.33
#   - Destination: ~/<project-root-name>/ (same name as local project folder)
# Excludes follow project rules.

REMOTE_USER=${REMOTE_USER:-root}
REMOTE_HOST=${REMOTE_HOST:-192.168.0.33}
REMOTE="${REMOTE_USER}@${REMOTE_HOST}"

# Resolve project root (repo root is the parent of this tools/ dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST_DIR_NAME="$(basename "${PROJECT_ROOT}")"  # Expected: Initializer
REMOTE_DEST=${REMOTE_DEST:-"~/${DEST_DIR_NAME}"}

DRY_RUN=false
DELETE=false

usage() {
  cat <<EOF
Usage: tools/sync-to-remote.sh [--dry-run|-n] [--delete|-d] [--host HOST|-H HOST] [--user USER|-u USER] [--dest REMOTE_PATH|-D REMOTE_PATH]

Options:
  --dry-run, -n          Show what would be transferred without making any changes
  --delete, -d           Delete extraneous files from destination dirs
  --host HOST, -H HOST   Override remote host (default: ${REMOTE_HOST})
  --user USER, -u USER   Override remote user (default: ${REMOTE_USER})
  --dest PATH, -D PATH   Override remote destination path (default: ${REMOTE_DEST})

Examples:
  tools/sync-to-remote.sh
  tools/sync-to-remote.sh --dry-run
  tools/sync-to-remote.sh -n
  tools/sync-to-remote.sh --delete --host 192.168.0.33 --user root
  tools/sync-to-remote.sh -d -H 192.168.0.33 -u root -D ~/Initializer
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|-n)
      DRY_RUN=true
      shift
      ;;
    --delete|-d)
      DELETE=true
      shift
      ;;
    --host|-H)
      REMOTE_HOST="$2"
      shift 2
      ;;
    --user|-u)
      REMOTE_USER="$2"
      shift 2
      ;;
    --dest|-D)
      REMOTE_DEST="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

# Recompose REMOTE after potential overrides
REMOTE="${REMOTE_USER}@${REMOTE_HOST}"

echo "Project root: ${PROJECT_ROOT}"
echo "Remote:       ${REMOTE}"
echo "Destination:  ${REMOTE_DEST}"

# Ensure remote destination exists
ssh -o StrictHostKeyChecking=accept-new "${REMOTE}" "mkdir -p ${REMOTE_DEST}"

RSYNC_FLAGS=("-avz" "--progress")
${DRY_RUN} && RSYNC_FLAGS+=("-n") || true
${DELETE} && RSYNC_FLAGS+=("--delete") || true

EXCLUDES=(
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=initializer-venv/"
  "--exclude=__pycache__/"
  "--exclude=*.pyc"
  "--exclude=.git/"
  "--exclude=.idea/"
  "--exclude=logs/"
  "--exclude=.DS_Store"
)

set -x
rsync "${RSYNC_FLAGS[@]}" "${EXCLUDES[@]}" \
  "${PROJECT_ROOT}/" "${REMOTE}:${REMOTE_DEST}/"
set +x

echo "✅ Sync complete."


