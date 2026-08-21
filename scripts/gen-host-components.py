#!/usr/bin/env python3
"""Generate host-specific mirrors of the canonical client components.

Some hosts only read a component from their own namespace directory. Rather than
hand-maintain copies that drift, they are generated from the canonical files:

    agents/<name>.md  ->  com.github.copilot/agents/<name>.agent.md

Usage:
    scripts/gen-host-components.py          # write the mirrors
    scripts/gen-host-components.py --check  # exit 1 if a mirror is stale
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPILOT_AGENTS = ROOT / "com.github.copilot" / "agents"


def mirrors():
    for src in sorted((ROOT / "agents").glob("*.md")):
        yield src, COPILOT_AGENTS / f"{src.stem}.agent.md"


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    COPILOT_AGENTS.mkdir(parents=True, exist_ok=True)
    for src, dest in mirrors():
        want = src.read_text()
        if dest.exists() and dest.read_text() == want:
            continue
        if check:
            stale.append(dest.relative_to(ROOT))
        else:
            dest.write_text(want)
            print(f"wrote {dest.relative_to(ROOT)}")

    known = {dest for _, dest in mirrors()}
    for orphan in COPILOT_AGENTS.glob("*.agent.md"):
        if orphan not in known:
            if check:
                stale.append(orphan.relative_to(ROOT))
            else:
                orphan.unlink()
                print(f"removed {orphan.relative_to(ROOT)}")

    if stale:
        print("stale host mirrors: " + ", ".join(str(s) for s in stale))
        print("run scripts/gen-host-components.py")
        return 1
    if check:
        print("host mirrors in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
