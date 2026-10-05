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
| [179](https://github.com/pts/pdfsizeopt/pull/179) | ECT aliases integrated; see toolchain record for current execution policy. |
| [178](https://github.com/pts/pdfsizeopt/pull/178) | Oxipng and Oxipng/ECT chain integrated; ECT now opt-in; use `--strip safe`; preflight both chain dependencies. |
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
| `lib/pdfsizeopt/main.py` Python runtime | Python 3 syntax, key-based sorting and integer division; explicit octet/file/struct/zlib boundaries; native file-object loading; failed atomic rename preserves existing files. |
| `lib/pdfsizeopt/main.py` image candidates | Oxipng/Zopfli defaults replace sam2p/PNGOUT/ECT; PNG reduction prepass (gray kept gray via `--nc`; rejected or failed Oxipng candidates are skipped, falling back to the rendered image) replaces repeat Oxipng run; qpdf predictor removal skipped unless sizes match exactly; retain original candidate. |
| `lib/pdfsizeopt/main.py` Ghostscript | Exact temporary read/write grants under SAFER; `.runtime/bin` replaces legacy bundle discovery. |
| `lib/pdfsizeopt/cff.py` | Python 3 integer/byte/hex boundaries, sorting, font-name error handling; symmetric numeric font comparison and optional PostScript difference detection; signed 32-bit dict operands. |
| `lib/pdfsizeopt/psproc.py` | Modern Ghostscript FontDirectory/CFF loader; remove obsolete `.setpdfwrite`. |
| `pdfsizeopt`, `mksingle.py` | Python 3/project environment launcher; standard zipapp generator with the same interpreter selection prepended. |
| `pdfsizeopt_test.py`, `extra/dvipdfmx_fontfix.py` | Python 3 syntax and byte contracts; UTF-8 helper file I/O, attached-map argument progress and argument-vector lookup. |
| `README.md`, `docker/*`, `docker_extraimgopt/*` | Current toolchain installation and unprivileged container, fork-aware Codespaces instructions. |
| `.gitignore`, `pdfsizeopt.single` | Generated single-file package is untracked and built from source, never edited by hand. |

Own files: `lib/pdfsizeopt/{binary,cli,image_filters}.py`, `pyproject.toml`,
`uv.lock`, `.dockerignore`, `docs/TOOLCHAIN.md`, `extra/*fork*`,
`extra/{preservation,font_preservation,python3_regression}_test.py`,
`.github/workflows/ci.yml`, this ledger and review evidence.
Architect reviewed the earlier incoming PR diffs before integration: conditional
GO with the preservation repairs above. Modernization adds Python 3 support;
no lossy mode is added. No incoming upstream commits were present at its start.

## Build and verify

See `README.md` for operating-system build dependencies. Setup keeps pinned
native tools inside ignored `.runtime/` and Python packages inside `.venv/`.

```sh
bash extra/setup_fork_tests.sh
bash extra/run_fork_tests.sh
.venv/bin/python mksingle.py
```

The runner exercises upstream parser/font tests, fork regressions, all-byte and
predictor regressions, 15 image cases through five optimizer configurations,
and embedded fonts with merging enabled and disabled. Both source and generated
archive are checked. Assertions cover identical renders at 72/144 dpi,
metadata, masks, text and unchanged JPEG/JP2 compressed payloads.

`./pdfsizeopt in.pdf out.pdf` uses the lossless default. Keep originals.
Multivalent and core-font unembedding remain disabled by default.

After committing, rehearse the entire patch set on current T-3B upstream:

```sh
bash extra/rehearse_upstream.sh
```

Rehearsal uses a separate clone/worktree, does not alter this checkout or its
refs, and retains its disposable directory for inspection. Conflicts fail
before tests. Run bughunt and no-mistakes before landing updates.
