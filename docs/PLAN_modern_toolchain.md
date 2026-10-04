# Modern pdfsizeopt toolchain

Requested: current stable Python and all tools used by this fork. Preserve image
samples, resolution, masks, colour information, embedded fonts and document
behaviour. Linux is the deployment target. Keep the working master as baseline.

## Phases

1. Inventory stable releases and existing ports. Closed pts PR 183 removes CFF,
   PostScript font processing and the upstream tests; do not adopt it wholesale.
2. Port the complete optimizer and tests to Python 3.14. Preserve the parser's
   byte-oriented string operations using explicit, reversible Latin-1 boundaries
   where appropriate; filesystem paths remain Unicode. No implicit encoding,
   newline conversion or process-wide monkeypatches. Replace vendored argparse
   and obsolete packaging with standard-library facilities where practical.
3. Replace the legacy binary bundle with verified, pinned modern dependencies.
   Exercise current Ghostscript font operations and image optimizer adapters.
   Obsolete tools need an explicit maintained replacement or documented result,
   never an unnoticed fallback to the old bundle. Multivalent remains disabled.
4. Validate original tests, fork regressions, image preservation and embedded
   fonts, source and packaged launchers, paths with spaces and Unicode, strict
   PDF validation, rendered equality and compression against the baseline.
5. Update installation, CI and fork seams. Review with bughunt; land only after
   no-mistakes and private-repository checks pass.

## Done

Python 3.14 runs the full feature set; production commands use verified current
stable tools; tests establish preservation; source and packaged installations
work; CI passes. A partial interpreter conversion is not completion.
