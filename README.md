# ASS to SRT

A small, dependency-free Python CLI for exporting plain UTF-8 subtitles from ASS dialogue events. It preserves dialogue text, commas, explicit line breaks and timing, strips styling tags, and rejects overlapping cues rather than silently merging them.

## 使用 / Usage

Requires Python 3.10 or newer on Windows, macOS or Linux. No network connection or API key is needed.

```sh
python export_final_ass_srt.py examples/sample.ass output/captions.srt
python -m unittest discover -v
```

The command writes `captions.srt` and a `captions.srt.json` record containing source/output SHA-256 hashes and cue count. Output directories are created automatically. Existing output files are replaced, so choose a separate output path; the input itself cannot be overwritten.

支持中文、逗号、ASS 显式换行和样式移除。仅转换字幕，不处理媒体、不上传文件、不验证语音准确性。示例内容为合成数据。

## Boundaries

- Input must contain an `[Events]` section whose `Format` includes `Start`, `End` and a final `Text` field.
- Empty, incomplete, overlapping, zero-duration and negative-time dialogue is rejected.
- ASS vector drawings are rejected. Karaoke timing, layout, animations, fonts and styling are not reproduced in SRT.
- Timestamps are rounded to milliseconds; output cues are sorted by start time.
- The optional metadata records local absolute paths. Review metadata before sharing it with others.

## Origin and license

Extracted and generalized from the author's private video-production tools. This repository includes only the standalone converter and synthetic examples/tests; no production media, accounts, client records or private repository history are included.

MIT license; see [LICENSE](LICENSE).
