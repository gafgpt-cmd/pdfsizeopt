# Public PDF benchmark, 2026-10-05

This comparison measures complete old and modern toolchains, not the Python
port in isolation. It uses eight public PDFs (3,789,363 input bytes), including
photographs, scanned text, bilevel, CMYK, JPEG2000 and multipage images.

## Revisions and commands

| Variant | Revision | Image setting |
|---|---|---|
| Old | `16ae3d3181cf1f55ab6855f39da7f8593844fbfb` | Legacy default, Python 2.7.12 and Ghostscript 9.05 bundle |
| Modern | `fffd067d569b10b894ea76a68c00b78796359ca3` | Default Oxipng + Oxipng/Zopfli + lossless JBIG2 |
| Modern without Zopfli | Same modern revision | `--use-image-optimizer=oxipng,jbig2` |

Each invocation uses a separate output PDF. Modern native versions are listed
in [TOOLCHAIN.md](TOOLCHAIN.md). The JBIG2 repair described below is not part of
these timed runs.

## Resource and timing controls

- Same Intel Core i5-1135G7 workstation; affinity to CPUs 0, 1, 2 and 3.
- Sequential invocations, with rotated variant order, not simultaneous jobs.
- Same systemd user cgroup: `MemoryMax=2G`, `MemoryLow=2G`,
  `MemorySwapMax=0`. These are a limit and memory-pressure protection, not an
  exclusive reservation of physical RAM. Observed peak was about 1.15 GiB,
  with no swapping, limit hits or OOM events.
- Inputs, outputs and temporary files on the same RAM-backed filesystem
  (tmpfs). Input bytes were read before each run. Disk throughput therefore
  was not the intended bottleneck; this is not a disk-performance benchmark.
- One untimed warmup per file/variant, then three timed runs: 24 warmup
  attempts and 72 measured attempts. The same 120-second cap applied to each
  attempt, including warmups that could not complete.
- Warm-cache comparison; no system-wide cache flush. CPU cache, turbo,
  temperature and background activity were not exclusively controlled.
  The governor was powersave; observed system load ranged from 2.87 to 5.21.
- Wall-clock measurements use Python's monotonic performance counter.
  Process completion polling can add up to roughly 50 ms. Small subsecond
  differences should not be interpreted as reliable speed rankings.
- Rendering and preservation checks ran after the timings.

These controls make the runs comparable on this machine; they do not create
identical hardware state or guarantee the same timing on another system.

## Aggregate result

Only the six PDFs successfully completed by all three variants are included.
The time is the sum of each file's median, not one combined invocation.

| Variant | Sum of median times | Combined output bytes |
|---|---:|---:|
| Old | 49.73 s | 1,793,474 |
| Modern default | 49.10 s | 1,789,104 |
| Modern without Zopfli | 12.09 s | 1,789,305 |

Without Zopfli the modern toolchain was about 4.1 times faster on this subset,
for 201 extra bytes compared with the modern default. Both use lossless image
settings. This small corpus does not establish a universal speed or size gain.

## Per-file results

Times below are medians of three runs. A timeout means all three attempts
reached the cap; a failure is not a fast successful result.

| Input | Variant | Median seconds / outcome | Output bytes |
|---|---|---:|---:|
| nasa-earth | Old | 0.616 | 317,897 |
| nasa-earth | Modern default | 0.667 | 317,861 |
| nasa-earth | Modern without Zopfli | 0.718 | 317,861 |
| tracemonkey | Old | 10.898 | 709,455 |
| tracemonkey | Modern default | 31.217 | 705,121 |
| tracemonkey | Modern without Zopfli | 4.333 | 705,322 |
| c03-29 | Old | 0.165 | 167,509 |
| c03-29 | Modern default | 0.316 | 167,509 |
| c03-29 | Modern without Zopfli | 0.316 | 167,509 |
| linn | Old | 37.574 | 72,471 |
| linn | Modern default | Failed (JBIG2) | — |
| linn | Modern without Zopfli | Failed (JBIG2) | — |
| ccitt | Old | 37.322 | 71,812 |
| ccitt | Modern default | 15.862 | 71,812 |
| ccitt | Modern without Zopfli | 5.686 | 71,812 |
| cmyk | Old | 0.366 | 486,118 |
| cmyk | Modern default | 0.517 | 486,118 |
| cmyk | Modern without Zopfli | 0.466 | 486,118 |
| lichtenstein | Old | 0.366 | 40,683 |
| lichtenstein | Modern default | 0.516 | 40,683 |
| lichtenstein | Modern without Zopfli | 0.567 | 40,683 |
| multipage | Old | Timeout (120 s) | — |
| multipage | Modern default | Timeout (120 s) | — |
| multipage | Modern without Zopfli | 66.088 | 739,991 |

## Preservation results and the discovered regression

All 20 successful file/variant combinations produced repeatable output bytes.
All 134 page-render comparisons at 72/144 dpi matched exactly; extracted text
matched, and qpdf structural checks returned success. Decoded image sets
matched; deduplication reduced the research paper's image count from 180 to
175, so image-count equality was not used as a preservation requirement.
JPEG/JP2 compressed payloads were unchanged. One NASA JPEG could not be decoded
by pikepdf in the checking script; its compressed payload and page renders
still matched exactly.

The `linn` JBIG2 scan succeeded with the old toolchain and failed with both
modern settings. Ghostscript's modern PostScript interface lacks the
`JBIG2Decode` filter used by this path. This is an actual compatibility
regression, not a compression-quality difference.

A separate local repair, `26a7d7f6e2ac8e53cfed3db08f3d9134876173f7` on
`fix/preserve-jbig2`, skips recompression of existing JBIG2 streams. On `linn`
it produced 72,487 bytes, versus the old version's 72,471, with unchanged JBIG2
payload and identical renders. It passed 87 regression tests, 160 synthetic
image conversions and font checks locally. It is **not merged** as of
2026-10-05; publication stopped when the external validation agent reached its
usage limit. This follow-up check must not be counted as a timed main-branch
success. See the [temporary workaround](USAGE.md#troubleshooting).

## Input provenance

The URLs below were downloaded on 2026-10-05. Branch-based URLs may change;
the SHA-256 identifies the actual input used. Verify a downloaded file with
`sha256sum filename.pdf` before treating a repeat as the same corpus. PDFs
are not redistributed in this repository.

| Input | Download | Bytes | SHA-256 |
|---|---|---:|---|
| nasa-earth | [NASA Earth lithograph](https://www.nasa.gov/wp-content/uploads/2009/12/Earth_Lithograph.pdf) | 364,563 | `f6850c067f126df43b212971468ac6b09729319224317abb7cf3288b5fe0974f` |
| tracemonkey | [Mozilla research paper](https://raw.githubusercontent.com/mozilla/pdf.js/master/test/pdfs/tracemonkey.pdf) | 1,016,315 | `3662ff519e485810520552bf301d8c3b2b917fd2f83303f4965d7abed367e113` |
| c03-29 | [Illustrated book scan](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/c03-29.pdf) | 167,938 | `c2ff83af7d028c95209cc7eebdf80fd5bb4cd292973ed6601e4bab7d1929f201` |
| linn | [Scanned two-column text](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/linn.pdf) | 75,273 | `e923f6e8e036185f8f2aae5f7fdeefd8ac658d627cebd4ebf630de4cbf0a2d64` |
| ccitt | [Bilevel CCITT scan](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/ccitt.pdf) | 103,856 | `5f4b129bf0eb0d32358a917cd1754c6fd68cac589ad79076b6d0191ebe84f0f1` |
| cmyk | [CMYK image](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/cmyk.pdf) | 897,087 | `6d3e47ad66c94d02436aca48f881a20f594bc0ded731001ebe4639497d697cd3` |
| lichtenstein | [JPEG2000 photograph](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/lichtenstein.pdf) | 44,040 | `d7f2f944de30876e21b10caa465bc617e8fbd00285bdd1fc648d39793ebd76f8` |
| multipage | [Multipage image document](https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources/multipage.pdf) | 1,120,291 | `07987c44650938fa8dcf08c0937691712fdd800669b4607c2c7e3fee21cb1f80` |

## Repeat the comparison

1. Prepare separate checkouts at the exact revisions above and their matching
   toolchains. Do not use the modern dependencies for the old baseline.
2. Download and checksum the same inputs. Use identical settings except for
   the explicit image-optimizer difference in the third variant.
3. Apply the same CPU affinity, cgroup memory/swap settings, tmpfs workspace
   and 120-second timeout to all variants. Record effective settings.
4. Warm each file/variant once, then run three sequential rounds with rotated
   order and fresh output paths. Capture exit status, elapsed time and size.
5. Record failures and timeouts separately. Compare only common successes
   when calculating aggregate speed and size.
6. After timing, validate outputs with the same qpdf and Poppler versions,
   compare every page at 72/144 dpi, extracted text and image payloads.

The original run logs and checking scripts are local benchmark artifacts;
this document records their results and protocol, not a shipped one-command
benchmark harness. The normal regression suite is reproducible using
`bash extra/run_fork_tests.sh`.
