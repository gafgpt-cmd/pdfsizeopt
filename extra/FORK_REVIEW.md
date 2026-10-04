# BugHunt: PR integration

2026-10-04. Scope: original PRs 165, 171, 178, 179, 180, 181, 186;
inherited T-3B compressor and image paths; their callers and new validation.

Confirmed and fixed:

| Severity / pattern | Failure | Regression evidence |
|---|---|---|
| Critical / E1 | External zlib output could decode to different pixels and still enter the PDF. | Stub returned compressed `wrong pixels` for `correct pixels`; baseline accepted it. Tests now reject wrong, empty, truncated and trailing output, and check existing PDFs survive failure. |
| Important / F1 | No image optimizer caused early return after deleting SMask/Metadata, changing transparency. | One-pixel RGB with SMask returned `None` for that association on baseline. Empty optimizer and skipped-Decode regressions now preserve associations. |
| Important / F3 | Zlib CLI checked the last image command, or an unbound variable when no image optimizer was selected. | Baseline CLI with `none` and a valid zlib template raised UnboundLocalError. Valid and invalid template tests now pass. |
| Important / A4 | External compressor selection persisted into later calls of main. | Two successive CLI invocations verify restoration of the standard compressor. |
| Important / E1 | Proposed Oxipng/ECT chain checked only the first executable. | Dependency fixtures omit each executable in turn; required mode rejects, optional mode skips the chain. |
| Important / E1 | Xref serialization padded omitted objects with zero offsets while omitting the type field, marking reserved object 0 as in-use. | GitHub's qpdf 11.x warned on rgb/none; official qpdf 11.9 reproduced it locally. The serializer now retains /Index, and a regression verifies the exact entries. |

Additional preservation decision: remove T-3B's unconditional Multivalent
structure/source-link stripping additions. Command-capture regression checks
that font unembedding remains opt-in. This is not a claim of live Multivalent
preservation; preservation runs explicitly disable it. Approved coverage
exception: no compatible live Multivalent engine was available, and Doc
approved shipping with Multivalent default-off without that live test.

Coverage: return contracts, cleanup on compressor failure, CLI boundaries,
empty and multi-megabyte inputs, malformed/truncated/wrong-type outputs,
failure before final output replacement, sequential-call state isolation,
file-path quoting, optional dependency behavior, rendered images and metadata.
No service write endpoints or signed/locked application state in this change.

Validation: 54 upstream tests; 17 focused regressions; 13 synthetic PDF cases
through six optimizer configurations for both source and rebuilt package.
Two render resolutions per output; JPEG/JP2 payload identity; metadata,
intent and soft-mask associations. See `extra/run_fork_tests.sh`.

Semgrep p/python and p/owasp-top-ten: zero findings and zero scan errors with
60-second rule timeout. Registry p/bash returned 404; ShellCheck covers the
three new shell scripts instead. New Python tests pass pycodestyle with the
repository's two-space convention and standard W503 exemption. No generated
program edited manually. Source fixture PDFs only; no private documents read.
