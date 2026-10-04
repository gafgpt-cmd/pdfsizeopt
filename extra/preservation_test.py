"""Synthetic PDF render, image payload and metadata checks (Python 3)."""

import base64
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib

import pikepdf
from PIL import Image, ImageCms


ROOT = Path(__file__).resolve().parents[1]


def run(args, env):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, timeout=120).stdout


def stream(attrs, data):
    return (b'<<' + attrs + b'/Length ' + str(len(data)).encode('ascii')
            + b'>>\nstream\n' + data + b'\nendstream')


def fixture(path, case):
    size = 32
    rgb = bytes(v for y in range(size) for x in range(size)
                for v in ((x * 8) % 256, (y * 8) % 256, 120))
    colors = b'/ColorSpace/DeviceRGB/BitsPerComponent 8'
    raw = rgb
    extra = b''
    special = None
    profile = b'<</Unused true>>'
    mask = stream(b'/Subtype/Image/Width 32/Height 32/ColorSpace/DeviceGray'
                  b'/BitsPerComponent 8/Filter/FlateDecode',
                  zlib.compress(bytes(x * 8 for y in range(size)
                                      for x in range(size))))
    if case == 'gray':
        colors = b'/ColorSpace/DeviceGray/BitsPerComponent 8'
        raw = bytes(x * 8 for y in range(size) for x in range(size))
    elif case == 'gray16':
        colors = b'/ColorSpace/DeviceGray/BitsPerComponent 16'
        raw = b''.join((x * 2000 + y).to_bytes(2, 'big')
                       for y in range(size) for x in range(size))
    elif case in ('bilevel', 'stencil'):
        colors = b'/ColorSpace/DeviceGray/BitsPerComponent 1'
        raw = b'\xaa\x55\xaa\x55' * size
        extra = b'/Decode[1 0]'
        if case == 'stencil':
            colors = b'/ImageMask true/BitsPerComponent 1'
    elif case == 'two-colour-rgb':
        raw = bytes(v for y in range(size) for x in range(size)
                    for v in ((255, 255, 255) if x % 2 else (0, 0, 0)))
    elif case == 'indexed':
        colors = (b'/ColorSpace[/Indexed/DeviceRGB 3'
                  b'<ff000000ff000000ffffffff>]/BitsPerComponent 8')
        raw = bytes(x % 4 for y in range(size) for x in range(size))
    elif case == 'soft-mask':
        extra = b'/SMask 6 0 R'
    elif case == 'colour-key':
        extra = b'/Mask[0 0 0 255 120 120]'
    elif case == 'custom-decode':
        extra = b'/Decode[0 .5 0 .5 0 .5]'
    elif case == 'icc':
        colors = b'/ColorSpace[/ICCBased 8 0 R]/BitsPerComponent 8'
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        profile = stream(b'/N 3', icc)
    elif case == 'cmyk':
        colors = b'/ColorSpace/DeviceCMYK/BitsPerComponent 8'
        raw = bytes(v for y in range(size) for x in range(size)
                    for v in (x * 8, y * 8, 0, 0))
    elif case in ('jpeg', 'jpeg2000'):
        image = Image.frombytes('RGB', (size, size), rgb)
        buf = io.BytesIO()
        image.save(buf, format='JPEG' if case == 'jpeg' else 'JPEG2000')
        raw = buf.getvalue()
        special = b'/DCTDecode' if case == 'jpeg' else b'/JPXDecode'
    image_data = raw if special else zlib.compress(raw, 1)
    attrs = (b'/Subtype/Image/Width 32/Height 32' + colors + extra
             + b'/Intent/RelativeColorimetric/Metadata 7 0 R/Filter'
             + (special or b'/FlateDecode'))
    objects = [
        b'<</Type/Catalog/Pages 2 0 R>>',
        b'<</Type/Pages/Kids[3 0 R]/Count 1>>',
        b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 220 240]'
        b'/Resources<</XObject<</Im0 4 0 R>>/Font<</F1 9 0 R>>>>'
        b'/Contents 5 0 R>>',
        stream(attrs, image_data),
        stream(b'', b'q 0.2 0.4 0.8 rg 160 0 0 160 20 20 cm /Im0 Do Q '
               b'BT /F1 10 Tf 20 210 Td (Synthetic preservation test) Tj ET'),
        mask,
        stream(b'/Type/Metadata/Subtype/XML',
               b'<x:xmpmeta xmlns:x="adobe:ns:meta/">synthetic</x:xmpmeta>'),
        profile,
        b'<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>',
    ]
    data = bytearray(b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(str(number).encode('ascii') + b' 0 obj\n' + obj + b'\nendobj\n')
    xref = len(data)
    data.extend(('xref\n0 %d\n0000000000 65535 f \n' % len(offsets)).encode('ascii'))
    for offset in offsets[1:]:
        data.extend(('%010d 00000 n \n' % offset).encode('ascii'))
    data.extend(('trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n' %
                 (len(offsets), xref)).encode('ascii'))
    path.write_bytes(data)
    return image_data if special else None


def image_objects(path, env):
    document = json.loads(run(['qpdf', '--json', '--json-stream-data=inline',
                               str(path)], env))
    return [value['stream'] for value in document['qpdf'][1].values()
            if value.get('stream', {}).get('dict', {}).get('/Subtype') == '/Image']


def main():
    work = Path(tempfile.mkdtemp(prefix='pdfsizeopt-preservation-'))
    env = os.environ.copy()
    env['HOME'] = str(work)
    env['PATH'] = str(ROOT / '.runtime/bin') + os.pathsep + env['PATH']
    python3 = os.environ.get('PYTHON3', str(ROOT / '.venv/bin/python'))
    launcher = os.environ.get('PDFSIZEOPT_LAUNCHER', str(ROOT / 'pdfsizeopt'))
    cases = ('rgb', 'gray', 'gray16', 'two-colour-rgb', 'indexed', 'bilevel', 'stencil',
             'soft-mask', 'colour-key', 'custom-decode', 'icc', 'cmyk',
             'jpeg', 'jpeg2000')
    optimizers = ('none', 'oxipng', 'oxipng_zopfli', 'jbig2', 'default')
    results = []
    for case in cases:
        source = work / (case + '.pdf')
        special = fixture(source, case)
        expected = {}
        for dpi in (72, 144):
            prefix = work / ('original-%s-%d' % (case, dpi))
            run(['pdftoppm', '-r', str(dpi), '-singlefile', str(source),
                 str(prefix)], env)
            expected[dpi] = prefix.with_suffix('.ppm').read_bytes()
        for optimizer in optimizers:
            output = work / ('%s-%s.pdf' % (case, optimizer))
            args = [python3, launcher, '--use-multivalent=no']
            if optimizer != 'default':
                args.append('--use-image-optimizer=' + optimizer)
            args += [str(source), str(output)]
            try:
                run(args, env)
                run(['qpdf', '--check', str(output)], env)
                for dpi in expected:
                    prefix = work / ('after-%s-%s-%d' % (case, optimizer, dpi))
                    run(['pdftoppm', '-r', str(dpi), '-singlefile', str(output),
                         str(prefix)], env)
                    assert prefix.with_suffix('.ppm').read_bytes() == expected[dpi], (
                        case, optimizer, dpi, 'render changed')
                images = image_objects(output, env)
                primary = [image for image in images
                           if image['dict'].get('/Intent') == '/RelativeColorimetric']
                assert len(primary) == 1, (case, optimizer, 'render intent lost')
                assert '/Metadata' in primary[0]['dict'], (case, optimizer, 'metadata lost')
                if case == 'gray16':
                    with pikepdf.Pdf.open(source) as before, pikepdf.Pdf.open(output) as after:
                        old = before.pages[0].Resources.XObject.Im0
                        new = after.pages[0].Resources.XObject.Im0
                        assert new.BitsPerComponent == 16
                        assert old.read_bytes() == new.read_bytes(), '16-bit samples changed'
                if case == 'soft-mask':
                    assert '/SMask' in primary[0]['dict'], 'soft mask lost'
                if special:
                    assert base64.b64decode(primary[0]['data']) == special, 'payload changed'
            except subprocess.CalledProcessError as error:
                raise RuntimeError('%s/%s: %s' %
                                   (case, optimizer, error.stderr.decode('utf-8', 'replace')))
            results.append({'case': case, 'optimizer': optimizer,
                            'before': source.stat().st_size,
                            'after': output.stat().st_size})
    (work / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    source = work / 'rgb.pdf'
    original = source.read_bytes()
    broken = work / 'broken-compressor.py'
    broken.write_text("import sys,zlib\nopen(sys.argv[1], 'wb').write("
                      "zlib.compress(b'wrong pixel data'))\n", encoding='utf-8')
    import shlex
    command = '%s %s %%(targetfnq)s' % (shlex.quote(python3), shlex.quote(str(broken)))
    for same_path in (False, True):
        output = source if same_path else work / 'existing-output.pdf'
        if not same_path:
            output.write_bytes(b'keep existing output')
        before = output.read_bytes()
        # Argument vector, no shell: environment selects the test interpreter only.
        # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args.dangerous-subprocess-use-tainted-env-args
        result = subprocess.run([python3, launcher, '--use-multivalent=no',
                                 '--use-image-optimizer=none',
                                 '--use-zlib-optimizer=' + command,
                                 str(source), str(output)], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=120)
        assert result.returncode != 0, 'invalid compressor was accepted'
        assert output.read_bytes() == before, 'failed optimization overwrote output'
        assert source.read_bytes() == original, 'failed optimization overwrote source'
    print('%d conversions: identical renders at 72/144 dpi; metadata, masks and '
          'JPEG/JP2 payloads verified. Evidence: %s' % (len(results), work))


if __name__ == '__main__':
    main()
