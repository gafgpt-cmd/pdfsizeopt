# Modern toolchain

Versions checked against upstream releases on 2026-10-04. Installation is
reproducible: native archives have SHA-256 pins, source builds use commit pins,
and Python packages use `uv.lock`. The supported target is Linux x86_64.

| Component | Version | Role / upstream |
|---|---|---|
| Python | 3.14.8 | [Runtime](https://www.python.org/downloads/release/python-3148/) |
| Ghostscript | 10.08.0 | [PDF image extraction and font conversion](https://ghostscript.com/releases/gsdnld.html) |
| Oxipng | 10.2.1 | [Lossless PNG reduction/compression](https://github.com/oxipng/oxipng/releases/tag/v10.2.1) |
| jbig2enc | 0.32 | [Lossless bilevel compression](https://github.com/agl/jbig2enc/releases/tag/0.32) |
| pikepdf | 10.16.0 | [qpdf-backed stream decoding](https://pikepdf.readthedocs.io/en/stable/topics/streams.html) |
| qpdf | 12.4.2 | [Structural validation](https://github.com/qpdf/qpdf/releases/tag/v12.4.2); also bundled in the pinned pikepdf wheel |
| Poppler | 26.10.0 | [Independent rendering and text checks](https://poppler.freedesktop.org/) |
| uv | 0.12.23 | [Locked project environment](https://github.com/astral-sh/uv/releases/tag/0.12.23) |
| Pillow | 12.3.0 | Synthetic image test fixtures |
| pycodestyle | 2.15.0 | Development lint dependency |

## Replacements

- Python 2 and the bundled legacy interpreter: Python 3.14 with an explicit
  binary boundary. PDF and font bytes retain a one-byte Latin-1 representation;
  this is not text transcoding. Paths remain Unicode.
- sam2p/png22pnm/tif22pnm: Oxipng reduces PNG palettes and bit depths. pikepdf
  removes PNG/TIFF predictors without changing packed samples, allowing a
  predictor-free Deflate candidate to compete with PNG compression.
- PNGOUT: Oxipng and its Zopfli mode compete with the original image.
  The proprietary PNGOUT executable is no longer installed or required.
- Python 2 executable generator: standard-library `zipapp`. The archive still
  requires the locked pikepdf environment and native programs.
- Ghostscript private font operators: supported font dictionaries and current
  CFF loader. SAFER remains enabled; temporary file access is granted explicitly.

ECT 0.9.5 reproduced a SIGSEGV on a large PNG in both serial and threaded
modes during validation. Oxipng with Zopfli replaces it in the supported
default; ECT is no longer installed.

Historical optimizer aliases remain opt-in for independently installed tools.
They are not part of the supported default installation. Multivalent remains
opt-in and is not installed. MozJPEG is not used: JPEG and JPEG2000 compressed
payloads are preserved rather than re-encoded. No downsampling, lossy JBIG2
symbol matching, or core-font unembedding is enabled.

## Verification

`bash extra/run_fork_tests.sh` runs parser/CFF regressions, byte-boundary and
predictor tests, source and archive optimization, and independent qpdf/Poppler
checks. Synthetic image cases cover RGB, grayscale, palettes, bilevel images,
stencils, soft masks, colour-key masks, custom Decode, ICC, CMYK, JPEG and JP2.
16-bit grayscale samples are checked byte-for-byte. Embedded Type 1 and CFF
font tests compare text and page renders with font merging on and off.

The input is retained. Run on a separate output and inspect important documents.
The suite establishes preservation for its tested cases, not all possible PDFs.

On the original 13 small image fixtures, the new default produced 19,915 bytes
in total versus 19,921 for the old default, with identical renders. A larger
3.4 MB PNG that crashed ECT completed with Oxipng/Zopfli and retained identical
decoded pixels. These are measured cases, not a universal compression ranking.
