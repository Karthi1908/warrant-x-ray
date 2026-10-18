"""Convenience entrypoint for architecture ablation study (AC-19)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to sys.path if not present
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from warrantx.eval.ablation import main

if __name__ == "__main__":
    main()
