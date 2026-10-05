# Usage and preservation

## Everyday commands

Run from the repository after [installation](../README.md#install-and-run).
Use separate input and output paths; keep the original.

```sh
# Faster lossless setting; explicit list replaces the default optimizer list.
./pdfsizeopt --use-image-optimizer=oxipng,jbig2 input.pdf output.pdf

# Current default: Oxipng, Oxipng/Zopfli and lossless JBIG2.
./pdfsizeopt input.pdf output.pdf

# Quoted paths work for spaces and Unicode.
./pdfsizeopt --use-image-optimizer=oxipng,jbig2 "My scan.pdf" "My scan small.pdf"

# Skip image optimization altogether; other PDF optimizations still run.
./pdfsizeopt --do-optimize-images=no input.pdf output.pdf

# Leave font optimization off.
./pdfsizeopt --do-optimize-fonts=no input.pdf output.pdf

# Complete option reference.
./pdfsizeopt --help
```

With just `input.pdf`, the normal output name is `input.pso.pdf`. An explicit
output path is easier to track. Check the process exit status before using it.

`--use-image-optimizer=none` disables the external optimizer list, but internal
image processing remains enabled. Use `--do-optimize-images=no` when the entire
image optimization stage must be skipped. Custom optimizer command patterns
execute shell commands; only use commands you trust.

## What is preserved

The supported settings do not downsample images, add JPEG loss, or use lossy
JBIG2 symbol matching. JPEG and JPEG2000 compressed payloads are retained.
Other supported images may change compression, palette or bit depth without
changing decoded pixel values. Identical images can be deduplicated.

Embedded fonts stay embedded by default. Type 1/CFF fonts can be rewritten or
merged, and PDF objects and streams can be reorganized. The result is therefore
not a byte-identical copy of the document. Multivalent and core-font removal
are disabled by default and are outside the supported preservation workflow.

The tests check rendered pages, text, masks, image metadata and compressed
JPEG/JP2 payloads. They do not establish universal preservation of every PDF
feature. Do not treat optimization as a way to preserve a digital signature:
rewriting signed bytes invalidates that signature.

## Why Zopfli is optional in the faster command

[Zopfli](https://github.com/google/zopfli) is a lossless Deflate compressor.
It uses more computation to find smaller representations compatible with
ordinary decoders. This fork invokes it through Oxipng; a separate `zopflipng`
installation is unnecessary.

Original pdfsizeopt supported ZopfliPNG but did not enable it by default.
In [the author's replacement discussion](https://github.com/pts/pdfsizeopt/issues/88),
he required reasonable speed and grayscale output suitable for transparency
masks. At that time ZopfliPNG lacked the required grayscale switch, while
pngwolf-zopfli was also much slower than PNGOUT. Those historical limitations
refer to those tools, not to the current Oxipng integration.

This fork enabled Oxipng/Zopfli by default during modernization to pursue
maximum lossless size reduction. The public benchmark supports offering the
explicit faster command for routine use. The documented command is a choice;
the program's default has not been changed.

## Check an output

The installed toolchain includes structural validation and an independent
renderer. These commands create separate inspection files:

```sh
.runtime/bin/qpdf --check output.pdf
.runtime/bin/pdftoppm -f 1 -singlefile -r 144 -png input.pdf input-first-page
.runtime/bin/pdftoppm -f 1 -singlefile -r 144 -png output.pdf output-first-page
.runtime/bin/pdftotext input.pdf input.txt
.runtime/bin/pdftotext output.pdf output.txt
```

Compare the two first-page images and text files. For important documents,
check all pages, especially fine detail, transparency and small text. A clean
qpdf check establishes structural validity, not visual equivalence. The
[automated preservation suite](../FORK.md#build-and-verify) checks its fixture
pages at 72 and 144 dpi through both source and packaged launchers.

## Troubleshooting

- **An image-heavy PDF takes a long time:** try the explicit
  `--use-image-optimizer=oxipng,jbig2` command. Already compressed photographs
  may have little room for lossless savings.
- **`/undefined in --filter--` involving JBIG2:** the benchmarked main revision
  `fffd067d569b10b894ea76a68c00b78796359ca3` attempts to decode some existing
  JBIG2 images through a PostScript filter unavailable in modern Ghostscript.
  Use `--do-optimize-images=no` to bypass that stage. See the
  [benchmark repair record](BENCHMARKS.md#preservation-results-and-the-discovered-regression)
  for the separate repair's revision, validation results and merge status.
- **Missing executables or Python dependencies:** rerun
  `bash extra/setup_fork_tests.sh` from this checkout. Use its launcher and
  project environment instead of the old upstream executable bundle.
- **Unsupported platform:** the pinned installer targets Linux x86_64.
  Native macOS, Windows and ARM builds are not covered by this setup.
- **Font changes in a particular document:** retry with
  `--do-optimize-fonts=no` and compare page renders and extracted text.

For a reproducible issue, record the commit, exact command, error output and
whether the input works with image or font optimization disabled. Share only
public or appropriately sanitized sample files.
