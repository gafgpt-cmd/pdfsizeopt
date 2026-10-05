# pdfsizeopt: modern lossless PDF optimization

Lossless PDF optimization for Linux x86_64, based on
[T-3B/pdfsizeopt](https://github.com/T-3B/pdfsizeopt) and
[pts/pdfsizeopt](https://github.com/pts/pdfsizeopt).

This fork runs on **Python 3.14.8** and **Ghostscript 10.08.0**. Its default image
pipeline compares Oxipng, Oxipng with Zopfli, lossless JBIG2 and the original
image. It also compares predictor-free compression using pikepdf/qpdf. It keeps
smaller candidates without downsampling or introducing lossy encoding.
JPEG and JPEG2000 compressed image data are left unchanged. Embedded fonts stay
embedded; Multivalent and core-font removal remain disabled by default.

## Choose a compression setting

For routine use, the measured faster setting keeps lossless Oxipng and JBIG2:

```sh
./pdfsizeopt --use-image-optimizer=oxipng,jbig2 input.pdf output.pdf
```

For an additional attempt at smaller images, use the current default:

```sh
./pdfsizeopt input.pdf output.pdf
```

The default also runs Oxipng with Zopfli. Both settings preserve image quality;
Zopfli spends extra CPU time searching for denser compression. It does not
increase resolution or improve pixels. On six public PDFs that all tested
versions completed, omitting Zopfli reduced aggregate time from 49.10 to 12.09
seconds, with just 201 additional output bytes. Results depend on the input;
see [benchmark methods, results and failures](docs/BENCHMARKS.md).

**Known issue in the benchmarked main revision:** some existing JBIG2 images
fail during Ghostscript extraction. Disabling Zopfli does not fix this. A
preservation repair has been tested on a separate branch but is not merged.
See [troubleshooting](docs/USAGE.md#troubleshooting) for the workaround and status.

## Install and run

Clone the repository, then enter its directory:

```sh
git clone https://github.com/gafgpt-cmd/pdfsizeopt.git
cd pdfsizeopt
```

On Ubuntu 24.04 or Debian 13 (Linux x86_64), install the build dependencies:

```sh
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config nasm curl git unzip ca-certificates \
  zlib1g-dev libssl-dev libffi-dev libjpeg-dev libpng-dev libtiff-dev \
  libleptonica-dev libfreetype6-dev libfontconfig1-dev libopenjp2-7-dev \
  liblcms2-dev libbrotli-dev libharfbuzz-dev libcairo2-dev
bash extra/setup_fork_tests.sh
./pdfsizeopt input.pdf output.pdf
```

The installer pins and verifies downloads, builds native tools under `.runtime/`,
and creates a locked Python environment in `.venv/`. It uses mise's Python 3.14.8
when available; otherwise uv obtains that interpreter. It does not change global
Python packages. Native builds need a compiler and development libraries.

The source launcher selects the project environment. Keep the input file and
write to a separate output. `--use-image-optimizer=none` disables external image
optimization. `--do-optimize-fonts=no` leaves font programs alone.

The old `pdfsizeopt_libexec` Python 2/Ghostscript 9 bundle is not loaded. sam2p,
PNGOUT, ECT and their helper tools are no longer required or installed. Historical
optimizer names remain available for explicit compatibility use if independently
installed; they are outside the supported default toolchain.

## Package and test

```sh
.venv/bin/python mksingle.py
.venv/bin/python pdfsizeopt.single input.pdf output.pdf
./pdfsizeopt.single input.pdf output.pdf  # Uses the adjacent .venv.
bash extra/run_fork_tests.sh
```

The generated `pdfsizeopt.single` is a standard Python executable archive. It
requires Python 3.14, the locked pikepdf dependency and the native tools; it does
not embed an obsolete interpreter. Source and archive run the same preservation
suite, including embedded fonts and paths containing spaces and Unicode.

```sh
docker build -f docker/Dockerfile -t pdfsizeopt:modern .
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" \
  pdfsizeopt:modern input.pdf output.pdf
docker run --rm --user root -w /opt/pdfsizeopt --entrypoint bash \
  pdfsizeopt:modern extra/run_fork_tests.sh
```

The container runs as an unprivileged user by default; the test suite rebuilds
the archive inside the image, so it needs `--user root`.

Codespaces can use the same installation commands in this checkout. Use the
repository's source or locally built archive, rather than downloading the old
upstream executable.

## Documentation

- [Usage and troubleshooting](docs/USAGE.md): settings, preservation boundaries,
  output checks and common failures.
- [Public PDF benchmark](docs/BENCHMARKS.md): timing, output sizes, image checks,
  input provenance and resource controls.
- [Toolchain](docs/TOOLCHAIN.md): pinned versions and replacement rationale.
- [Fork maintenance](FORK.md): inherited PRs, modified upstream seams and tests.

## Versions and maintenance

See [the toolchain record](docs/TOOLCHAIN.md) for version pins, replacements and
validation, and [FORK.md](FORK.md) for upstream PR provenance, changed seams and
update rehearsal. The original project documentation is available
[upstream](https://github.com/pts/pdfsizeopt/blob/master/README.md); its legacy
installation instructions do not apply to this fork.

Original author: Peter Szabo. The project retains its GNU GPL v2-or-later licence;
see [LICENSE](LICENSE). Upstream's optimization paper and presentation remain in
`pts_pdfsizeopt2009/` and `pts_pdfsizeopt2009_talk/`.
