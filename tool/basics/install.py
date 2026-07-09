"""Basics — no installation needed (reference-only cheatsheet)."""

from pathlib import Path


def install(dest: Path) -> int:
    print("Basics è un cheatsheet di riferimento, non richiede installazione.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(install(Path.cwd()))
