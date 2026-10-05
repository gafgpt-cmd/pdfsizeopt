"""Behavior regressions for the private fork; run with Python 2.7."""

import os
import shlex
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'lib'))
from pdfsizeopt import binary
from pdfsizeopt.binary import buffer, open_octets
from pdfsizeopt import main


class ForkRegressionTest(unittest.TestCase):
  def setUp(self):
    self.scratch = tempfile.mkdtemp(prefix='pdfsizeopt-test-')
    self.saved = []
    self.env = os.environ.copy()
    os.environ['HOME'] = self.scratch
    os.environ['PATH'] = self.scratch
    self.patch(main, 'TMP_PREFIX', os.path.join(self.scratch, 'tmp.'))
    self.patch(main, 'compat_compress', binary.compress)
    self.patch(main, 'GetLibexecDir', lambda unused: None)
    self.patch(main, 'PrependToPath', lambda unused: None)
    self.patch(main, 'FindExeOnPath', lambda name: name)
    self.patch(main, 'RedirectOutput', lambda cmd, mode: cmd)
    self.patch(main.os, 'system', self.unexpected_command)

  def patch(self, owner, name, value):
    self.saved.append((owner, name, getattr(owner, name)))
    setattr(owner, name, value)

  def tearDown(self):
    for owner, name, value in reversed(self.saved):
      setattr(owner, name, value)
    os.environ.clear()
    os.environ.update(self.env)

  def unexpected_command(self, cmd):
    self.fail('Unstubbed command: ' + cmd)

  def cli(self, *args):
    return main.main(['pdfsizeopt', '--use-multivalent=no',
                      '--do-debug-image-optimizers=yes'] + list(args))

  def external(self, result, status=0, create=True):
    def run(cmd):
      args = shlex.split(cmd)
      if create:
        with open_octets(args[-1], 'wb') as f:
          f.write(result)
      return status
    self.patch(main.os, 'system', run)

  def test_zlib_without_image_optimizer(self):
    self.cli('--use-image-optimizer=none',
             '--use-zlib-optimizer=fake %(sourcefnq)s %(targetfnq)s')

  def test_zlib_requires_its_own_target_placeholder(self):
    self.assertRaises(SystemExit, self.cli, '--use-zlib-optimizer=fake input')

  def test_zlib_rejects_unknown_placeholder(self):
    self.assertRaises(SystemExit, self.cli,
                      '--use-zlib-optimizer=fake %(wrong)s %(targetfnq)s')

  def test_zlib_state_does_not_leak_to_next_invocation(self):
    self.cli('--use-zlib-optimizer=fake %(targetfnq)s')
    self.cli('--use-image-optimizer=none')
    self.assertIs(main.compat_compress, binary.compress)

  def test_zlib_rejects_corrupt_truncated_wrong_and_trailing_output(self):
    data = 'preserve these pixels' * 500
    for output in ('', 'bad', binary.compress(data)[:-1],
                   binary.compress('different'), binary.compress(data) + 'junk'):
      self.external(output)
      self.assertRaises(SystemExit, main.ZlibCmd, data, 9,
                        'fake %(sourcefnq)s %(targetfnq)s')
      self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_larger_valid_output_uses_baseline(self):
    data = 'repeat pixel' * 1000
    self.external(binary.compress(data, 0))
    self.assertEqual(binary.compress(data, 9), main.ZlibCmd(
        data, 9, 'fake %(sourcefnq)s %(targetfnq)s'))
    self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_smaller_valid_output_is_kept(self):
    data = 'repeat pixel' * 1000
    output = binary.compress(data, 9)
    self.external(output)
    self.assertEqual(output, main.ZlibCmd(data, 1, 'fake %(targetfnq)s'))
    self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_empty_input(self):
    self.external(binary.compress(''))
    self.assertEqual('', binary.decompress(main.ZlibCmd(
        '', 9, 'fake %(sourcefnq)s %(targetfnq)s')))

  def test_zlib_failure_and_missing_output_clean_up(self):
    for status in (256, 0):
      self.external('', status=status, create=False)
      self.assertRaises(SystemExit, main.ZlibCmd, 'data', 9,
                        'fake %(sourcefnq)s %(targetfnq)s')
      self.assertEqual([], os.listdir(self.scratch))

  def image_pdf(self, extra=''):
    pdf = main.PdfData()
    obj = main.PdfObj(None)
    obj.head = ('<</Subtype/Image/Width 1/Height 1/BitsPerComponent 8'
                '/ColorSpace/DeviceRGB/Filter/FlateDecode/SMask 2 0 R'
                '/Metadata 3 0 R/Intent/RelativeColorimetric%s>>' % extra)
    obj.stream = binary.compress('\xff\x00\x00')
    obj.Set('Length', len(obj.stream))
    pdf.objs = {1: obj}
    return pdf

  def test_no_image_optimizers_preserves_mask_and_metadata(self):
    pdf = self.image_pdf()
    before = pdf.objs[1].head, pdf.objs[1].stream
    pdf.OptimizeImages([], False)
    self.assertEqual(before, (pdf.objs[1].head, pdf.objs[1].stream))
    self.assertEqual([], os.listdir(self.scratch))

  def test_skipped_decode_preserves_mask_and_metadata(self):
    pdf = self.image_pdf('/Decode[0 .5 0 .5 0 .5]')
    before = pdf.objs[1].Get('SMask'), pdf.objs[1].Get('Metadata')
    pdf.OptimizeImages(['fake %(targetfnq)s'], False)
    self.assertEqual(before, (pdf.objs[1].Get('SMask'),
                              pdf.objs[1].Get('Metadata')))

  def test_oxipng_chain_preflights_both_tools(self):
    for missing in ('ect', 'oxipng'):
      self.patch(main, 'FindExeOnPath',
                 lambda name, missing=missing: name != missing)
      self.assertRaises(SystemExit, self.cli,
                        '--use-image-optimizer=oxipng_ect')

  def test_optional_missing_chain_does_not_run(self):
    self.patch(main, 'FindExeOnPath', lambda name: name == 'oxipng')
    self.cli('--use-image-optimizer=oxipng_ect',
             '--do-require-image-optimizers=no')

  def test_optimizer_commands_preserve_alias_and_threading(self):
    image = main.ImageData()
    image.width = image.height = 1
    image.bpc = 8
    image.color_type = 'rgb'
    image.is_inverted = image.is_interlaced = False
    image.compression = 'zip-png'
    image.idat = binary.compress('\0\xff\0\0')
    source = os.path.join(self.scratch, "image with ' quote.png")
    image.SavePng(source)
    calls = []
    self.patch(main.os, 'system', lambda cmd: calls.append(shlex.split(cmd)) or 0)
    for alias in ('ect', 'ECT', 'oxipng', 'oxipng_ect'):
      target = os.path.join(self.scratch, 'out-' + alias + '.png')
      result = main.PdfData.ConvertImage(source, target,
          main.IMAGE_OPTIMIZER_CMD_MAP[alias], alias)
      self.assertEqual(image.idat, result[1].idat)
      args = calls[-1]
      self.assertEqual(alias.split('_')[0], args[0])
      if 'ect' in alias.lower():
        self.assertIn('--mt-deflate', args)
      if alias == 'oxipng_ect':
        self.assertEqual('ect', args[args.index('&&') + 1])
      self.assertEqual(target, args[-1])

  def test_multivalent_preserves_structure_and_requires_font_opt_in(self):
    pdf = main.PdfData()
    self.patch(main.PdfData, 'AppendSerializedPdf', lambda unused, **kwargs: 0)
    calls = []

    def run(cmd):
      args = shlex.split(cmd)
      calls.append(args)
      with open_octets(args[-1][:-4] + '-o.pdf', 'wb') as f:
        f.write('%PDF-1.4\nsynthetic output')
      return 0

    self.patch(main.os, 'system', run)
    for remove in (False, True):
      pdf._RunMultivalent(False, 'fake-multivalent', remove)
      self.assertNotIn('-nostruct', calls[-1])
      self.assertNotIn('-nowebcap', calls[-1])
      self.assertEqual(remove, '-nocore' in calls[-1])

  def test_large_zlib_input_round_trips(self):
    data = 'all pixels must remain unchanged' * 65536
    self.external(binary.compress(data, 9))
    self.assertEqual(data, binary.decompress(main.ZlibCmd(
        data, 9, 'fake %(sourcefnq)s %(targetfnq)s')))

  def test_xref_without_type_field_omits_reserved_object_zero(self):
    trailer = main.PdfObj(None)
    trailer.head = '<< /Root 1 0 R >>'
    main.PdfData.GenerateXrefStream(
        [1, 2], {1: 15, 2: 65}, 109, trailer, 3, None, None,
        is_flate_ok=False)
    self.assertEqual('[0 1 0]', trailer.Get('W'))
    self.assertEqual('[1 3]', trailer.Get('Index'))
    self.assertEqual('\x0f\x41\x6d', trailer.stream)

  def predictor_pdf(self, rows):
    pdf = main.PdfData()
    obj = main.PdfObj(None)
    obj.head = ('<</Subtype/Image/Width 4/Height 2/BitsPerComponent 8'
                '/ColorSpace/DeviceGray/Filter/FlateDecode'
                '/DecodeParms<</Predictor 15/Colors 1/Columns 4>>>>')
    obj.stream = binary.compress(''.join('\0' + row for row in rows))
    obj.Set('Length', len(obj.stream))
    pdf.objs = {1: obj}
    return pdf

  def record_optimizers(self):
    calls = []

    def run(cmd):
      args = shlex.split(cmd)
      calls.append(args[0])
      if args[0] == 'fake':
        with open_octets(args[-2], 'rb') as source:
          data = source.read()
        with open_octets(args[-1], 'wb') as target:
          target.write(data)
      return 0

    self.patch(main.os, 'system', run)
    return calls

  def test_mismatched_predictor_rows_keep_original_samples(self):
    for rows in (['\x10\x20\x30\x40', '\x50\x60\x70\x80', '\x90\xa0\xb0\xc0'],
                 ['\x10\x20\x30\x40', '\x50\x60']):
      pdf = self.predictor_pdf(rows)
      calls = self.record_optimizers()
      pdf.OptimizeImages(['fake %(sourcefnq)s %(targetfnq)s'], False)
      self.assertEqual(['fake'], calls)
      self.assertEqual(''.join('\0' + row for row in rows),
                       binary.decompress(pdf.objs[1].stream))

  def test_oxipng_reduction_runs_once(self):
    pdf = self.predictor_pdf(['\x10\x20\x30\x40', '\x50\x60\x70\x80'])
    calls = self.record_optimizers()
    pdf.OptimizeImages([main.IMAGE_OPTIMIZER_CMD_MAP['oxipng']], False)
    self.assertEqual(['oxipng'], calls)
    pdf = self.predictor_pdf(['\x10\x20\x30\x40', '\x50\x60\x70\x80'])
    calls = self.record_optimizers()
    pdf.OptimizeImages([main.IMAGE_OPTIMIZER_CMD_MAP['oxipng'],
                        'fake %(sourcefnq)s %(targetfnq)s'], False)
    self.assertEqual(['oxipng', 'fake'], calls)


if __name__ == '__main__':
  unittest.main(verbosity=2)
