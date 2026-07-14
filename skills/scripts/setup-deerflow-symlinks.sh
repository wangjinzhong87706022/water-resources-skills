#!/usr/bin/env bash
# ============================================================================
# setup-deerflow-symlinks.sh
#
# Generates the `public/` symlink layer for deer-flow Schema B integration.
#
# Layout after running:
#   skills/
#   ├── public/               ← NEW (gitignored, regenerated as needed)
#   │   ├── water-situation -> ../water-situation
#   │   ├── rainfall         -> ../rainfall
#   │   ├── ...              (11 skills + shared + lib + scripts)
#   │
#   ├── shared/    lib/    scripts/    docs/    ← real files (unchanged)
#   └── water-situation/   ...               ← real skill dirs (unchanged)
#
# The `public/` directory itself is gitignored; only the script is committed.
# Run this after adding/removing skills, or when switching deer-flow integration modes.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLIC_DIR="$ROOT_DIR/public"

echo "▶ ROOT_DIR  = $ROOT_DIR"
echo "▶ PUBLIC_DIR = $PUBLIC_DIR"
echo

# ── 1. Fresh public/ ──────────────────────────────────────────────────────
if [ -d "$PUBLIC_DIR" ]; then
  echo "ℹ  public/ already exists — removing stale symlinks"
  find "$PUBLIC_DIR" -maxdepth 1 -type l -delete
else
  echo "➕  Creating public/"
  mkdir -p "$PUBLIC_DIR"
fi

# ── 2. Skill directories to expose ─────────────────────────────────────────
# Add/remove names here when skills change.
SKILL_NAMES=(
  water-situation
  rainfall
  water-quality
  water-forecast
  gate-pump-operation
  water-warning
  water-fusion
  water-visualization
  build-dashboard
  create-viz
  data-context-extractor
)

# ── 3. Shared/dependency directories ───────────────────────────────────────
SHARED_DIRS=(
  shared
  lib
  scripts
)

# ── 4. Create skill symlinks ────────────────────────────────────────────────
echo "▶ Creating skill symlinks …"
for name in "${SKILL_NAMES[@]}"; do
  src="$ROOT_DIR/$name"
  dst="$PUBLIC_DIR/$name"
  if [ ! -d "$src" ]; then
    echo "  ⚠  Skipping $name — source dir not found: $src"
    continue
  fi
  if [ -L "$dst" ]; then
    rm "$dst"
  fi
  ln -s "../$name" "$dst"
  echo "  ✔  public/$name -> ../$name"
done

# ── 5. Create shared/dependency symlinks ───────────────────────────────────
echo
echo "▶ Creating shared/dependency symlinks …"
for name in "${SHARED_DIRS[@]}"; do
  src="$ROOT_DIR/$name"
  dst="$PUBLIC_DIR/$name"
  if [ ! -d "$src" ]; then
    echo "  ⚠  Skipping $name — source dir not found: $src"
    continue
  fi
  if [ -L "$dst" ]; then
    rm "$dst"
  fi
  ln -s "../$name" "$dst"
  echo "  ✔  public/$name -> ../$name"
done

# ── 6. Summary ─────────────────────────────────────────────────────────────
echo
echo "✅  Done. Symlink tree:"
find "$PUBLIC_DIR" -maxdepth 1 -type l -printf '  %p -> %l\n' | sort
echo
echo "Next: set DEER_FLOW_SKILLS_PATH=$ROOT_DIR and restart deer-flow."
