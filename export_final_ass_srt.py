#!/usr/bin/env python3
"""Export plain UTF-8 SRT from the final ASS events.

The ASS event text and timecodes are the only input. Styling tags are removed,
while ASS line breaks are retained as SRT line breaks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


def stamp(value: str) -> tuple[int, str]:
    if not re.fullmatch(r"\d+:\d{2}:\d{2}(?:\.\d+)?", value.strip()):
        raise ValueError("Invalid ASS timestamp")
    hours, minutes, seconds = value.strip().split(":")
    try:
        total = Decimal(hours) * 3600 + Decimal(minutes) * 60 + Decimal(seconds)
    except InvalidOperation as error:
        raise ValueError("Invalid ASS timestamp") from error
    if int(minutes) >= 60 or Decimal(seconds) >= 60:
        raise ValueError("Timestamp minutes and seconds must be below 60")
    milliseconds = int((total * 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return milliseconds, (
        f"{milliseconds // 3600000:02}:"
        f"{milliseconds // 60000 % 60:02}:"
        f"{milliseconds // 1000 % 60:02},{milliseconds % 1000:03}"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def convert(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("Input and output must be different files")
    fields = None
    in_events = False
    rows = []
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("["):
            in_events = line.strip().lower() == "[events]"
            fields = None
        if not in_events:
            continue
        if line.startswith("Format:"):
            fields = [field.strip() for field in line.split(":", 1)[1].split(",")]
            if not {'Start', 'End', 'Text'}.issubset(fields) or fields[-1] != 'Text':
                raise ValueError("ASS events require Start, End and a final Text field")
        if not line.startswith("Dialogue:"):
            continue
        if not fields:
            raise ValueError("Missing ASS event format")
        values = line.split(":", 1)[1].lstrip().split(",", len(fields) - 1)
        if len(values) != len(fields):
            raise ValueError("Incomplete ASS dialogue event")
        event = dict(zip(fields, values))
        if re.search(r"\\p\s*[1-9]\d*", event['Text']):
            raise ValueError("ASS vector drawing events are not supported")
        text = re.sub(r"\{[^}]*\}", "", event["Text"])
        text = text.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")
        if not text.strip():
            continue
        start_ms, start = stamp(event["Start"])
        end_ms, end = stamp(event["End"])
        if start_ms >= end_ms:
            raise ValueError("Invalid cue duration")
        rows.append((start_ms, end_ms, start, end, text))

    rows.sort(key=lambda row: row[0])
    if not rows:
        raise ValueError("No captions")
    if any(first[1] > second[0] for first, second in zip(rows, rows[1:])):
        raise ValueError("Overlapping ASS events require explicit merge")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n\n".join(
            f"{index}\n{start} --> {end}\n{text}"
            for index, (_, _, start, end, text) in enumerate(rows, 1)
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "source": str(source.resolve()),
        "source_sha256": sha256(source),
        "srt": str(output.resolve()),
        "srt_sha256": sha256(output),
        "cues": len(rows),
        "text_and_timing": "EXACT_FINAL_ASS_EXPORT",
        "style_removed": True,
        "audio_realign": False,
        "notes": "SRT stores text/time; ASS retains styling. Exporting SRT does not reburn video or prove speech accuracy.",
    }
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    metadata = convert(args.source, args.output)
    args.output.with_suffix(".srt.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
