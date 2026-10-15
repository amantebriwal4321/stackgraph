"""Fail if docs contain an em dash, an en dash, or a double hyphen."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "README.md", ROOT / "LICENSE", *sorted((ROOT / "docs").glob("*.md"))]


def main() -> None:
    failed = False
    for path in FILES:
        if not path.exists():
            print(f"missing {path}")
            failed = True
            continue
        text = path.read_text(encoding="utf-8")
        if "\u2014" in text or "\u2013" in text:
            print(f"{path}: em dash or en dash")
            failed = True
        for number, line in enumerate(text.splitlines(), start=1):
            if "--" in line:
                print(f"{path}:{number}: double dash")
                failed = True
    if failed:
        raise SystemExit(1)
    print(f"checked {len(FILES)} files")


if __name__ == "__main__":
    main()
