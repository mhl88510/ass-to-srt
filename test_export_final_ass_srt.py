import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from export_final_ass_srt import convert, stamp


class SubtitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'captions.ass'
        self.output = self.root / 'nested' / 'captions.srt'

    def write(self, rows, fmt='Layer, Start, End, Style, Text'):
        self.source.write_text('[Script Info]\nTitle: Synthetic fixture\n[Events]\nFormat: '+fmt+'\n'+rows, encoding='utf-8-sig')

    def test_unicode_commas_style_and_linebreaks(self):
        self.write(r'Dialogue: 0,0:00:01.20,0:00:02.35,Default,{\b1}你好, world\N第二行\h结束'+'\n')
        metadata = convert(self.source, self.output)
        self.assertEqual(self.output.read_text(encoding='utf8'), '1\n00:00:01,200 --> 00:00:02,350\n你好, world\n第二行 结束\n')
        self.assertEqual(metadata['srt_sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(metadata['source_sha256'], hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_sorted_adjacent_cues(self):
        self.write('Dialogue: 0,0:00:02.00,0:00:03.00,Default,Second\nDialogue: 0,0:00:01.00,0:00:02.00,Default,First\n')
        convert(self.source, self.output)
        self.assertLess(self.output.read_text().index('First'), self.output.read_text().index('Second'))

    def test_overlap_rejected_before_output(self):
        self.write('Dialogue: 0,0:00:01.00,0:00:03.00,Default,A\nDialogue: 0,0:00:02.00,0:00:04.00,Default,B\n')
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            convert(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_times(self):
        for value in ['-1:00:00.00','0:60:00.00','0:00:60.00','nan','0:1:01']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                stamp(value)
        self.assertEqual(stamp('0:59:59.9995')[1], '01:00:00,000')

    def test_malformed_and_drawing_events(self):
        for rows, fmt in [('Dialogue: 0,0:00:01.00\n','Layer, Start, End, Style, Text'),
                          ('Dialogue: 0,0:00:01.00,0:00:02.00,Default,{\\p1}m 0 0 l 1 1\n','Layer, Start, End, Style, Text'),
                          ('','Text, Start, End')]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.write(rows, fmt)
                convert(self.source, self.output)

    def test_empty_and_zero_duration(self):
        for rows in ['', 'Dialogue: 0,0:00:01.00,0:00:01.00,Default,Text\n']:
            self.write(rows)
            with self.assertRaises(ValueError):
                convert(self.source, self.output)

    def test_input_cannot_be_overwritten(self):
        self.write('Dialogue: 0,0:00:01.00,0:00:02.00,Default,Text\n')
        original = self.source.read_bytes()
        with self.assertRaises(ValueError):
            convert(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), original)

    def test_command_line_writes_metadata(self):
        self.write('Dialogue: 0,0:00:00.00,0:00:01.00,Default,Example\n')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('export_final_ass_srt.py')), str(self.source), str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = json.loads(self.output.with_suffix('.srt.json').read_text())
        self.assertEqual(metadata['cues'], 1)


if __name__ == '__main__':
    unittest.main()
