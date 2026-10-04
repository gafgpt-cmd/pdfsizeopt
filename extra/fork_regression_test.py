"""Behavior regressions for the private fork; run with Python 2.7."""

import os
import shlex
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'lib'))
from pdfsizeopt import main


class ForkRegressionTest(unittest.TestCase):
  def setUp(self):
    self.scratch = tempfile.mkdtemp(prefix='pdfsizeopt-test-')
    self.saved = []
    self.env = os.environ.copy()
    os.environ['HOME'] = self.scratch
    os.environ['PATH'] = self.scratch
    self.patch(main, 'TMP_PREFIX', os.path.join(self.scratch, 'tmp.'))
    self.patch(main, 'compat_compress', zlib.compress)
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
        with open(args[-1], 'wb') as f:
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
    self.assertIs(main.compat_compress, zlib.compress)

  def test_zlib_rejects_corrupt_truncated_wrong_and_trailing_output(self):
    data = 'preserve these pixels' * 500
    for output in ('', 'bad', zlib.compress(data)[:-1],
                   zlib.compress('different'), zlib.compress(data) + 'junk'):
      self.external(output)
      self.assertRaises(SystemExit, main.ZlibCmd, data, 9,
                        'fake %(sourcefnq)s %(targetfnq)s')
      self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_larger_valid_output_uses_baseline(self):
    data = 'repeat pixel' * 1000
    self.external(zlib.compress(data, 0))
    self.assertEqual(zlib.compress(data, 9), main.ZlibCmd(
        data, 9, 'fake %(sourcefnq)s %(targetfnq)s'))
    self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_smaller_valid_output_is_kept(self):
    data = 'repeat pixel' * 1000
    output = zlib.compress(data, 9)
    self.external(output)
    self.assertEqual(output, main.ZlibCmd(data, 1, 'fake %(targetfnq)s'))
    self.assertEqual([], os.listdir(self.scratch))

  def test_zlib_empty_input(self):
    self.external(zlib.compress(''))
    self.assertEqual('', zlib.decompress(main.ZlibCmd(
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
    obj.stream = zlib.compress('\xff\x00\x00')
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
    image.idat = zlib.compress('\0\xff\0\0')
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
      with open(args[-1][:-4] + '-o.pdf', 'wb') as f:
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
    self.external(zlib.compress(data, 9))
    self.assertEqual(data, zlib.decompress(main.ZlibCmd(
        data, 9, 'fake %(sourcefnq)s %(targetfnq)s')))


if __name__ == '__main__':
  unittest.main(verbosity=2)
