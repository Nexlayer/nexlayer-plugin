#!/usr/bin/env bash
# Sync the shipped skills and tool list from the MCP server repo, which is the
# source of truth for both. Everything under skills/ is a verbatim copy of
# Nexlayer/claudecode-mcp-go plus the patches in patches/ — never hand-edit it
# here; edit it upstream, or edit the patch, and re-sync.
#
#   scripts/sync-from-mcp.sh              # clone the MCP repo and sync
#   scripts/sync-from-mcp.sh --check      # report drift, change nothing
#   scripts/sync-from-mcp.sh /path/to/mcp # sync from a local checkout
#
# Exit 1 in --check mode means the plugin has drifted from canon.

set -euo pipefail

REPO="git@github.com:Nexlayer/claudecode-mcp-go.git"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECK=0
SRC=""

for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    *) SRC="$arg" ;;
  esac
done

if [[ -z "$SRC" ]]; then
  SRC="$(mktemp -d)/mcp-src"
  echo "Cloning $REPO ..."
  git clone --depth 1 -q "$REPO" "$SRC"
fi

if [[ ! -d "$SRC/skills" ]]; then
  echo "error: $SRC does not look like the MCP repo (no skills/ directory)" >&2
  exit 2
fi

echo "MCP source: $SRC"
[[ -d "$SRC/.git" ]] && echo "MCP commit: $(git -C "$SRC" rev-parse --short HEAD) $(git -C "$SRC" log -1 --format=%ci)"

# --- skills -----------------------------------------------------------------
# Build canon+patches in a staging tree, then either install it or diff the
# shipped tree against it. Patches are the only sanctioned deviation from canon
# and are documented in patches/README.md.
STAGE="$(mktemp -d)/skills"
mkdir -p "$STAGE"
for skill in ship-it-nexlayer debug-nexlayer; do
  if [[ ! -d "$SRC/skills/$skill" ]]; then
    echo "error: $skill missing from the MCP repo — did it get renamed?" >&2
    exit 2
  fi
  cp -R "$SRC/skills/$skill" "$STAGE/$skill"
  rm -f "$STAGE/$skill/AGENTS.md"          # contributor doc for the MCP repo
  find "$STAGE/$skill" -name .DS_Store -delete
done

shopt -s nullglob
patches=("$ROOT"/patches/*.patch)
shopt -u nullglob
if (( ${#patches[@]} )); then
  for p in "${patches[@]}"; do
    # git apply, not patch(1): strict context, no fuzz, no .orig droppings.
    # Patch paths are repo-rooted (a/skills/...), and $STAGE is the skills dir,
    # so strip two leading components.
    if (cd "$STAGE" && git apply -p2 --whitespace=nowarn "$p" 2>/tmp/patcherr); then
      echo "  applied: patches/$(basename "$p")"
    else
      echo "error: patches/$(basename "$p") no longer applies — upstream changed the file." >&2
      sed 's/^/       /' /tmp/patcherr >&2
      echo "       Regenerate it against current canon or delete it; see patches/README.md." >&2
      exit 3
    fi
  done
else
  echo "  no patches"
fi

drift=0
for skill in ship-it-nexlayer debug-nexlayer; do
  if [[ $CHECK -eq 1 ]]; then
    if diff -rq "$STAGE/$skill" "$ROOT/skills/$skill" >/tmp/skilldiff 2>&1; then
      echo "  in sync: skills/$skill"
    else
      drift=1
      echo "  DRIFTED: skills/$skill"
      sed 's/^/      /' /tmp/skilldiff
    fi
  else
    rm -rf "$ROOT/skills/$skill"
    cp -R "$STAGE/$skill" "$ROOT/skills/$skill"
    echo "  synced: skills/$skill"
  fi
done

# --- tool list --------------------------------------------------------------
tools="$(mktemp)"
{
  grep -rhoE '"nexlayer(AI)?_[a-z_]+"' "$SRC/internal/tools" "$SRC/types" "$SRC/cmd" 2>/dev/null \
    | tr -d '"' | grep -v '^nexlayerAI_deploy_$'
  # sandbox deploy tools are registered per catalog slug at runtime
  grep -oE 'Slug:[[:space:]]+"[a-z-]+"' "$SRC/internal/sandboxes/catalog.go" \
    | sed -E 's/.*"([a-z-]+)"/\1/' | tr '-' '_' | sed 's/^/nexlayerAI_deploy_/'
} | sort -u > "$tools"

if [[ $CHECK -eq 1 ]]; then
  if diff -q "$tools" "$ROOT/scripts/mcp-tools.txt" >/dev/null; then
    echo "  in sync: scripts/mcp-tools.txt ($(wc -l < "$tools" | tr -d ' ') tools)"
  else
    drift=1
    echo "  DRIFTED: scripts/mcp-tools.txt"
    diff "$ROOT/scripts/mcp-tools.txt" "$tools" | sed 's/^/      /'
  fi
else
  cp "$tools" "$ROOT/scripts/mcp-tools.txt"
  echo "  synced: scripts/mcp-tools.txt ($(wc -l < "$tools" | tr -d ' ') tools)"
fi

echo
if [[ $CHECK -eq 1 && $drift -eq 1 ]]; then
  echo "Plugin has drifted from the MCP repo. Run without --check to resync."
  exit 1
fi

python3 "$ROOT/scripts/validate.py"
