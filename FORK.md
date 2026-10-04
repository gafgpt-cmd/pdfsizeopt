# Private pdfsizeopt fork

Origin: `gafgpt-cmd/pdfsizeopt` (private). Upstream: `T-3B/pdfsizeopt`.
Original: `pts/pdfsizeopt`. Both public remotes are push-disabled locally.
Base: `0af13e98d36205168b7699813da3cfddd019946b` (2026-08-22).

## PR inventory (2026-10-04)

T-3B has no open PRs. Original has seven:

| Original PR | Outcome |
|---|---|
| [186](https://github.com/pts/pdfsizeopt/pull/186) | Already inherited from T-3B; preservation bugs repaired below. |
| [181](https://github.com/pts/pdfsizeopt/pull/181) | README typo integrated. |
| [180](https://github.com/pts/pdfsizeopt/pull/180) | Lowercase `ect` executable supported; uppercase alias retained. |
| [179](https://github.com/pts/pdfsizeopt/pull/179) | Threaded Deflate enabled for both ECT aliases. |
| [178](https://github.com/pts/pdfsizeopt/pull/178) | Oxipng and Oxipng/ECT chain integrated, optional; use `--strip safe`; preflight both chain dependencies. |
| [171](https://github.com/pts/pdfsizeopt/pull/171) | Already functionally satisfied by upstream 2bab160: v9 runtime and corrected executable list. Blanket chmod not needed. |
| [165](https://github.com/pts/pdfsizeopt/pull/165) | Codespaces instructions adapted to execute this checkout, not download old pts code. |

## Upstream seams

| File | Change to preserve during updates |
|---|---|
| `lib/pdfsizeopt/main.py` optimizer map/discovery | PR178–180 combination; check both built-in chain programs. |
| `lib/pdfsizeopt/main.py` ZlibCmd/main | Validate template independently; reset compressor per invocation; verify complete exact zlib round-trip, reject trailing data, keep smaller of valid result and baseline; unique temporary names and failure cleanup. |
| `lib/pdfsizeopt/main.py` OptimizeImages | Skip unavailable optimizers before mutation; stage metadata changes on a copy so skipped images retain SMask, Metadata and Intent. |
| `lib/pdfsizeopt/main.py` GenerateXrefStream | Retain /Index when the type field is omitted; zero padding would mark reserved object 0 as in-use at byte offset zero. Caught by qpdf 11.x on Ubuntu CI. |
| `lib/pdfsizeopt/main.py` _RunMultivalent | Remove T-3B's added unconditional `-nostruct -nowebcap`. Core-font unembedding remains explicit/default-off. |
| `README.md` | PR181 typo, fork-aware Codespaces/build instructions. |
| `.gitignore`, `pdfsizeopt.single` | Generated single-file package is untracked and built from source, never edited by hand. |

Own files: `extra/*fork*`, `extra/preservation_test.py`,
`extra/test-requirements.txt`, `.github/workflows/ci.yml`, this ledger.
Architect reviewed incoming diffs before integration: conditional GO with the
preservation repairs above. No Python 3 migration or lossy mode added.

## Build and verify

Linux x86_64; compiler, make, CMake, curl, git, uv, qpdf, Poppler and advzip
must be available. Setup keeps dependencies inside ignored `.runtime/` and
`.venv/`; it does not install system packages.

```sh
bash extra/setup_fork_tests.sh
bash extra/run_fork_tests.sh
```

After setup, build only the distributable from the checkout root with:

```sh
PATH="$PWD/.runtime/bin:$PATH" .runtime/python2/bin/python2.7 "$PWD/mksingle.py"
```

The runner executes upstream tests, fork regressions, and 13 synthetic PDF
cases through six optimizer configurations. It builds `pdfsizeopt.single`
with the existing generator, then repeats preservation tests through it.
Assertions cover identical renders at 72/144 dpi, image metadata/intent,
soft masks and unchanged JPEG/JP2 compressed payloads. These fixtures are
evidence for the tested cases, not a guarantee for every possible PDF.

For a source-only invocation: `./pdfsizeopt --use-multivalent=no in.pdf out.pdf`.
Keep originals. `--do-remove-core-fonts=no` remains the default. Multivalent's
legacy stripping behavior is not recommended for strict preservation.

After committing, rehearse the entire patch set on current T-3B upstream:

```sh
bash extra/rehearse_upstream.sh
```

Rehearsal uses a separate clone/worktree, does not alter this checkout or its
refs, and retains its disposable directory for inspection. Conflicts fail
before tests. Run bughunt and no-mistakes before landing updates.
