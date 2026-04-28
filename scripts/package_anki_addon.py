#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_SOURCE = PROJECT_ROOT / "anki_addon" / "jlpt_coverage"
SHARED_PACKAGE = PROJECT_ROOT / "jlpt_converge"
PYTHON_I18N = PROJECT_ROOT / "python_i18n"
VOCAB_CSV = PROJECT_ROOT / "data" / "jlpt_vocab.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "jlpt_coverage.ankiaddon"

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".git", ".gitignore")


def copy_source(staging_dir: Path) -> None:
    shutil.copytree(ADDON_SOURCE, staging_dir, dirs_exist_ok=True, ignore=IGNORE)
    shutil.copytree(SHARED_PACKAGE, staging_dir / "jlpt_converge", dirs_exist_ok=True, ignore=IGNORE)
    shutil.copytree(PYTHON_I18N, staging_dir / "python_i18n", dirs_exist_ok=True, ignore=IGNORE)
    data_dir = staging_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VOCAB_CSV, data_dir / "jlpt_vocab.csv")


def zip_addon(staging_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging_dir))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package the JLPT Coverage Anki add-on.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output .ankiaddon path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not ADDON_SOURCE.exists():
        raise FileNotFoundError(f"Missing add-on source directory: {ADDON_SOURCE}")
    if not SHARED_PACKAGE.exists():
        raise FileNotFoundError(f"Missing shared package directory: {SHARED_PACKAGE}")
    if not (PYTHON_I18N / "i18n" / "__init__.py").exists():
        raise FileNotFoundError(
            f"Missing python_i18n submodule: {PYTHON_I18N}\nRun: git submodule update --init --recursive"
        )
    if not VOCAB_CSV.exists():
        raise FileNotFoundError(
            f"Missing vocabulary CSV: {VOCAB_CSV}\nRun: python3 scripts/extract_jlpt_vocab.py"
        )

    with tempfile.TemporaryDirectory(prefix="jlpt_coverage_addon_") as temp_dir:
        staging_dir = Path(temp_dir)
        copy_source(staging_dir)
        zip_addon(staging_dir, args.output.expanduser())

    print(f"Wrote {args.output.expanduser()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
