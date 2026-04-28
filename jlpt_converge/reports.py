from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .core import vocab_status_fieldnames


def write_vocab_status_report(
    report_dir: Path,
    rows: list[dict[str, str]],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = report_dir / f"jlpt_vocab_status_{stamp}.csv"

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=vocab_status_fieldnames(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return output_path
