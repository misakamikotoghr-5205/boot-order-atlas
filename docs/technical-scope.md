# Technical scope · v0.1.0

Checked against QNX SDP **8.0** public documentation on **2026-11-09**. Atlas reads supplied text only. It never resolves referenced host files, sources scripts, runs commands, contacts services, or changes a buildfile.

## Source basis

- [OS Image Buildfiles](https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.building/topic/buildfiles/buildfile.html): distinguishes image contents and startup order. Atlas reviews the latter, not the resulting image.
- [The script file](https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.building/topic/buildfiles/nto_script.html): identifies `+script`, file concatenation and modifier scope. Atlas preserves supplied block order and single-line versus inherited modifiers.
- [Buildfile syntax](https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.building/topic/buildfiles/buildfile_syntax.html): describes attributes and multiline inline file boundaries. Atlas does not attempt the full grammar or evaluate inline escaping.
- [mkifs, Script files](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/m/mkifs.html): basis for background execution, foreground return risk, internal commands and `+external`. Atlas models literal internal `waitfor path [seconds]` and `reopen [path [seconds]]`; defaults are `/dev/console` for `reopen` and 5.0 seconds. `procmgr_symlink` is recorded source-first, link-second, without readiness inference.
- [waitfor utility](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/w/waitfor.html): the external utility has an additional polling argument. Atlas keeps it separate. A successful path `stat()` is not a health test; network-interface readiness may need other commands, which Atlas does not infer.

No documentation text, vendor code, SDK headers, toolchains, target binaries or BSPs are redistributed. Examples are original, intentionally incomplete review inputs.

## Model decisions

| Evidence | Atlas conclusion | It does not establish |
| --- | --- | --- |
| Literal producer launch before consumer | A declared producer was ordered earlier | Successful spawn or created resource |
| Later internal path wait | A conditional stat barrier is present | Wait success, health, or continued existence |
| Foreground `blocks` declaration | Later events blocked under that declaration | A measured OS hang |
| Foreground `returns` declaration | Order can continue under that declaration | Readiness of a background child |
| Foreground `unknown` or unmodeled command | Subsequent reachability is unproven | That QNX rejects the command |
| Contract cycle | Declared before-launch dependencies conflict | A universal runtime deadlock |
| Multiple resource providers | Ambiguous ownership | Which provider will actually satisfy the path |
| Missing provider declaration | Model lacks a source | That no external source exists |

`conditional_stat_barrier` requires an earlier declared provider and an ordered intervening wait. A wait placed before its producer cannot guard a later consumer in this model. Initial resources bypass producer checks because the operator explicitly declares them present. Dependency-cycle edges use only unique providers and exclude initially available resources.

All waits are treated as potentially expiring. The tool never emits a `ready`, `safe`, `boot_success`, or runtime-health verdict. It does not calculate boot time or add up timeout values as a timing guarantee. Resources can disappear after checks, and arbitrary executables may spawn children, detach, change paths or fail. Those behaviors require target validation.

## Explicit boundaries

Literal path matching is exact: no relative paths, symlink/prefix resolution, shell expansion, host environment interpolation, wildcarding, generated scripts or includes are analyzed. Image attributes are not validated. Recognized build-time transform attributes are flagged. Unknown constructs remain visible as coverage gaps; later script reachability is conservative.

Only inline blocks whose opening and closing braces occupy their normal separate lines are read. Leading bracket groups are parsed to distinguish `external`, `critical`, `session`, `argv0`, `cpu` and `pri`; scheduling, privileges and session correctness are not verified. Modifier/environment assignment lines are retained in the timeline. Literal environment values are recorded, not executed or expanded.

The HTML includes supplied source and contract data. Review/redact sensitive buildfile text before sharing it. It has no remote assets, JavaScript, forms or telemetry. Reports are deterministic; source and canonical contract fingerprints are for reproducibility, not signatures or authenticity claims.

Input bounds: 1 MiB UTF-8 source, 20,000 source lines, 2,000 script events; 256 KiB contract JSON, 128 services, 64 paths per path list, 32 prefix tokens. Only LF/CRLF delimit source lines; bare CR, Unicode line separators and other control characters (apart from tab) are rejected rather than manufacturing extra commands. Duplicate JSON keys, non-finite constants, unknown contract keys and nonliteral contract paths are rejected. The CLI refuses output paths that resolve to an input or to another selected output and writes each report via atomic replacement. Two reports are not a transactional pair if a later filesystem write fails.
