"""Binary preservation and packed predictor regressions for the Python port."""

import os
import base64
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from pdfsizeopt import binary, cff, image_filters, main


class Python3RegressionTest(unittest.TestCase):
    def test_every_byte_round_trips_without_newline_conversion(self):
        data = bytes(range(256)) + b'\r\n\r\x00\x85\xa0\xff'
        encoded = binary.string(data)
        self.assertEqual(len(data), len(encoded))
        self.assertEqual(data, binary.octets(encoded))
        path = Path(tempfile.mkdtemp()) / 'café 漢字.pdf'
        with binary.open_octets(path, 'wb') as stream:
            stream.write(encoded)
        self.assertEqual(data, path.read_bytes())
        with binary.open_octets(path, 'rb') as stream:
            stream.seek(13)
            self.assertEqual('\r', stream.read(1))
            stream.seek(1, os.SEEK_CUR)
            self.assertEqual(15, stream.tell())
            stream.seek(0)
            self.assertEqual(encoded, stream.read())

    def test_unsigned_png_crc_and_binary_struct_fields(self):
        data = binary.pack('>L4s', 0xffffffff, b'IDAT')
        self.assertEqual((0xffffffff, 'IDAT'), binary.unpack('>L4s', data))
        self.assertEqual(zlib.crc32(bytes(range(256))),
                         binary.crc32(binary.string(bytes(range(256)))))

    def test_qpdf_preserves_packed_one_two_four_and_eight_bit_samples(self):
        for bits in (1, 2, 4, 8):
            width = 13
            row_bytes = (width * bits + 7) // 8
            raw = bytes(range(row_bytes)) + bytes(reversed(range(row_bytes)))
            # Second row uses PNG's Up predictor, including its padding bits.
            predicted = (b'\0' + raw[:row_bytes] + b'\2' +
                         bytes((raw[row_bytes + i] - raw[i]) & 255
                               for i in range(row_bytes)))
            actual = image_filters.unfilter(zlib.compress(predicted), 10, 1,
                                            bits, width)
            self.assertEqual(raw, actual, bits)

    def test_ghostscript_filters_preserve_every_byte(self):
        data = bytes(range(256))
        encoded_cases = [
            ('ASCII85Decode', base64.a85encode(data) + b'~>'),
            ('ASCIIHexDecode', data.hex().encode('ascii') + b'>'),
            ('RunLengthDecode', b'\x7f' + data[:128] + b'\x7f' + data[128:] + b'\x80'),
        ]
        previous_prefix = main.TMP_PREFIX
        try:
            main.TMP_PREFIX = tempfile.mkdtemp() + '/decode.'
            for filter_name, encoded in encoded_cases:
                with self.subTest(filter=filter_name):
                    obj = main.PdfObj(None)
                    obj.head = '<</Filter/%s>>' % filter_name
                    obj.stream = binary.string(encoded)
                    self.assertEqual(data, binary.octets(obj.GetUncompressedStream()))
        finally:
            main.TMP_PREFIX = previous_prefix

    def test_font_comparison_detects_changes_in_both_directions(self):
        self.assertFalse(cff.IsCffValueEqual('1', '100'))
        self.assertFalse(cff.IsCffValueEqual('100', '1'))
        self.assertTrue(cff.IsCffValueEqual('1', '1.0001'))
        original = {'Private': {}, 'CharStrings': {},
                    'Encoding': ['/.notdef'] * 256, 'FontName': 'Fixture'}
        changed = dict(original, Private={'ParsedPostScript': {'foo': 1}})
        self.assertEqual(['/ParsedPostScript'],
                         cff.GetParsedCffDifferences(original, changed))

    def test_failed_rename_retains_existing_files(self):
        work = Path(tempfile.mkdtemp())
        source, target = work / 'source', work / 'target'
        source.write_bytes(b'new')
        target.write_bytes(b'original')
        with mock.patch.object(main.os, 'rename', side_effect=PermissionError('denied')):
            with self.assertRaises(SystemExit) as error:
                main.Rename(str(source), str(target))
        self.assertEqual(4, error.exception.code)
        self.assertEqual(b'new', source.read_bytes())
        self.assertEqual(b'original', target.read_bytes())

    def test_tex_helper_accepts_attached_map_argument(self):
        work = Path(tempfile.mkdtemp())
        (work / 'config').write_text('f default.map\n', encoding='utf-8')
        (work / 'font.map').write_text(
            'ptmr8r Times-Roman "TeXBase1Encoding ReEncodeFont" <8r.enc\n',
            encoding='utf-8')
        helper = Path(__file__).resolve().parent / 'dvipdfmx_fontfix.py'
        script = r"""
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('helper', sys.argv[1])
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
calls = []
def lookup(args, **kwargs):
    calls.append(args)
    return str(Path('config' if len(args) == 3 else 'font.map').resolve()) + '\n'
helper.subprocess.check_output = lookup
helper.os.execlp = lambda *args: calls.append(list(args))
helper.main(['helper', '-fmap with spaces', 'input.dvi'])
print(json.dumps(calls))
"""
        result = subprocess.run([sys.executable, '-c', script, str(helper)],
                                cwd=work, capture_output=True, text=True,
                                check=True, timeout=30)
        calls = json.loads(result.stdout)
        self.assertIn(['kpsewhich', 'map with spaces'], calls)
        self.assertEqual('dvipdfmx', calls[-1][0])
        self.assertIn('ptmr8r 8r Times-Roman',
                      (work / 'dvipdfmx_base.map').read_text(encoding='utf-8'))

    def test_octet_file_object_loading(self):
        path = Path(__file__).resolve().parent / 'small.pdf'
        pdf = main.PdfData().Load(str(path))
        with path.open('rb') as source:
            loaded = main.PdfData().Load(source)
        self.assertEqual(len(pdf.objs), len(loaded.objs))


if __name__ == '__main__':
    unittest.main()
