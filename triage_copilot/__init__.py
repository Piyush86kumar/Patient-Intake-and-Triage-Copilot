from __future__ import annotations

from pathlib import Path

# This shim makes the src-layout package importable when running from the
# repository root (useful for uvicorn --reload which spawns subprocesses).
# Compute the repository root as the parent of this package directory.
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
SRC_PKG = REPO_ROOT / "src" / "triage_copilot"
if SRC_PKG.exists():
    __path__.insert(0, str(SRC_PKG))
