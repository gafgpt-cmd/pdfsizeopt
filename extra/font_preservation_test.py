"""Exercise embedded Type 1/CFF fonts, merging, Unicode paths and current Ghostscript."""

import os
from pathlib import Path
import subprocess
import tempfile

import pikepdf

from preservation_test import ROOT, run


def create_type1_pdf(path):
    """Synthetic two-glyph encrypted Type 1 font with a triangular A."""
    header = (
        b'%!PS-AdobeFont-1.0: FixtureType1 1.0\n11 dict begin\n'
        b'/FontName /FixtureType1 def\n/FontType 1 def\n/PaintType 0 def\n'
        b'/FontMatrix [0.001 0 0 0.001 0 0] def\n'
        b'/FontBBox [0 0 500 700] def\n/Encoding StandardEncoding def\n'
        b'currentdict end\ncurrentfile eexec\n')

    def encrypt(data, seed):
        out = bytearray()
        for byte in data:
            cipher = byte ^ (seed >> 8)
            out.append(cipher)
            seed = ((cipher + seed) * 52845 + 22719) & 65535
        return bytes(out)

    private = (
        b'xxxxdup /Private 8 dict dup begin /lenIV 4 def /BlueValues [] def '
        b'/password 5839 def '
        b'/RD {string currentfile exch readstring pop} executeonly def '
        b'/ND {noaccess def} executeonly def end readonly put\n'
        b'dup /Private get begin\ndup /CharStrings 2 dict dup begin\n')
    for name, code in [(b'.notdef', '8bf8ec0d0e'),
                       (b'A', '8bf8ec0d8b8b15f78ef95005f78efd5005fc888b05090e')]:
        char = encrypt(b'xxxx' + bytes.fromhex(code), 4330)
        private += (b'/' + name + b' ' + str(len(char)).encode('ascii') +
                    b' RD ' + char + b' ND\n')
    private += (b'end readonly put\nend\ndup /FontName get exch definefont '
                b'pop\nmark currentfile closefile\n')
    cipher = encrypt(private, 55665)
    trailer = b'\n' + b'0' * 512 + b'\ncleartomark\n'
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(300, 300))
        stream = pdf.make_stream(header + cipher + trailer)
        stream.Length1 = len(header)
        stream.Length2 = len(cipher)
        stream.Length3 = len(trailer)
        descriptor = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.FontDescriptor, FontName=pikepdf.Name.FixtureType1,
            Flags=32, FontBBox=[0, 0, 500, 700], ItalicAngle=0, Ascent=700,
            Descent=0, CapHeight=700, StemV=80, FontFile=stream))
        font = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.FixtureType1, FirstChar=65, LastChar=65,
            Widths=[600], FontDescriptor=descriptor,
            Encoding=pikepdf.Name.WinAnsiEncoding))
        page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
        page.Contents = pdf.make_stream(b'BT /F1 40 Tf 40 150 Td (AAAA) Tj ET')
        pdf.save(path)


def main():
    work = Path(tempfile.mkdtemp(prefix='pdfsizeopt-fonts-')) / 'fonts café 漢字'
    work.mkdir()
    env = os.environ.copy()
    env['PATH'] = str(ROOT / '.runtime/bin') + os.pathsep + env['PATH']
    python = os.environ.get('PYTHON3', str(ROOT / '.venv/bin/python'))
    launcher = os.environ.get('PDFSIZEOPT_LAUNCHER', str(ROOT / 'pdfsizeopt'))
    parts = []
    for index, text in enumerate(('ABC abc 0123 fi fl', 'XYZ xyz 4567 $ % &')):
        ps = work / ('part%d.ps' % index)
        pdf = ps.with_suffix('.pdf')
        ps.write_text('%!PS\n<< /NeverEmbed [] >> setdistillerparams\n'
                      '/Helvetica findfont 24 scalefont setfont\n'
                      '72 700 moveto (' + text + ') show\n'
                      '/Times-Roman findfont 18 scalefont setfont\n'
                      '72 650 moveto (' + text + ') show\nshowpage\n',
                      encoding='utf-8')
        run(['gs', '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pdfwrite',
             '-dEmbedAllFonts=true', '-sOutputFile=' + str(pdf), str(ps)], env)
        parts += [str(pdf), '1']
    type1 = work / 'type1.pdf'
    create_type1_pdf(type1)
    parts += [str(type1), '1']
    source = work / 'source.pdf'
    run(['qpdf', '--empty', '--pages'] + parts + ['--', str(source)], env)
    original = source.read_bytes()
    fonts = run(['pdffonts', str(source)], env)
    assert b'Type 1C' in fonts, fonts
    expected_text = run(['pdftotext', str(source), '-'], env)
    for unify in ('yes', 'no'):
        target = work / ('output-' + unify + '.pdf')
        command = [python, launcher, '--use-multivalent=no',
                   '--use-image-optimizer=none', '--do-unify-fonts=' + unify,
                   '--do-double-check-type1c-output=yes', str(source), str(target)]
        try:
            run(command, env)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(error.stderr.decode('utf-8', 'replace')) from error
        run(['qpdf', '--check', str(target)], env)
        output_fonts = run(['pdffonts', str(target)], env).splitlines()[2:]
        assert output_fonts and all(line.split()[-5] == b'yes' for line in output_fonts)
        assert run(['pdftotext', str(target), '-'], env) == expected_text
        for page in (1, 2, 3):
            for dpi in (72, 144):
                rendered = []
                for path in (source, target):
                    prefix = work / ('render-' + path.stem)
                    run(['pdftoppm', '-f', str(page), '-r', str(dpi),
                         '-singlefile', str(path), str(prefix)], env)
                    rendered.append(prefix.with_suffix('.ppm').read_bytes())
                assert rendered[0] == rendered[1], (unify, page, dpi)
        assert source.read_bytes() == original
    print('Embedded fonts: identical text and renders, both merge modes; %s' % work)


if __name__ == '__main__':
    main()
