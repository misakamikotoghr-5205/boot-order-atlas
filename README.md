# Boot Order Atlas

Review QNX SDP 8.0 `mkifs` startup order on your host before a target is available. The CLI connects inline startup commands to explicitly declared resource dependencies, shows missing or misplaced path waits, and compares two revisions with source-line evidence.

**This is a working host-side static tool. It does not invoke `mkifs`, run QNX/QEMU, validate an IFS image, or prove a successful boot.** Included `workshop-*` programs are fictional review fixtures, with no supplied binaries. No SDK, QNX license, account, network access, model, or hardware is required to run Atlas.

## Run locally

Python 3.10+; standard library only. From this directory:

```sh
python3 -m boot_order_atlas analyze examples/serial-before.build \
  --contract examples/serial-contract.json \
  --json output/before.json --html output/before.html

python3 -m boot_order_atlas compare \
  examples/serial-before.build examples/serial-after.build \
  --contract examples/serial-contract.json \
  --json output/comparison.json --html output/comparison.html
```

Open `output/comparison.html` in a browser. It is one script-free HTML file, works offline, and includes the timeline, declared dependency edges, diagnostics, original text, and line links. The JSON contains the same analysis plus source and contract SHA-256 fingerprints. Identical inputs produce identical artifacts.

The first example launches a panel after its producers but before any matching waits: two `RESOURCE_UNGUARDED` warnings. The revised example adds waits before the panel. Its requirements become `conditional_stat_barrier`; the report continues to warn that finite `stat()` waits do not establish health or eliminate timeout risk.

Other examples:

```sh
python3 -m boot_order_atlas analyze examples/cycle.build \
  --contract examples/cycle-contract.json
python3 -m boot_order_atlas analyze examples/boundaries.build \
  --contract examples/empty-contract.json
```

## What you declare

`serial-contract.json` is a review model, not a QNX configuration format. Each service has a stable ID, a literal `argv_prefix`, `provides`, `requires`, and a `foreground` return assumption. `requires` means the resource must exist **before this command is launched**. It does not describe dependencies that an application waits for internally.

`foreground` is `blocks`, `returns`, or `unknown`. It is deliberately explicit: a foreground resource manager may daemonize and return. Returning alone is never treated as resource readiness. `initial_resources` are operator assumptions; Atlas never examines the host `/dev` tree. Incorrect declarations produce incorrect model conclusions.

Overlapping command prefixes and multiple declared providers remain ambiguous. No driver-to-device mapping is guessed. Edit or review the contract when executable arguments, lifecycle behavior, or ownership of a path changes. See [contract and API](docs/contract-and-api.md).

## Supported review scope

- Ordered multiline inline `[+script] name = { … }` blocks, including a standalone global `+script` attribute.
- Literal command tokens, environment assignments, trailing `&`, and known startup modifiers with global or single-command scope.
- Internal `waitfor`, `reopen` defaults, and recorded `procmgr_symlink` source/link order. A symlink does not imply target readiness.
- Contract-relative unstarted/unmodeled/unguarded resources, foreground blocking and unknown return behavior, ambiguous declarations, and dependency cycles.
- Event changes, line moves, introduced/no-longer-reported diagnostics, contract changes, and a textual source diff. Removing a diagnostic is not an observed runtime repair.

The reader is intentionally narrower than QNX's parser. External scripts, explicit shells, expansion, escaped inline characters, continuations, unsupported modifiers, shell-like operators and nonliteral waits produce **coverage gaps**. External `waitfor` under `+external` is an ordinary unmodeled executable unless separately declared, not silently interpreted as the internal command. Image layout, binaries, library availability, permissions, security policy, scheduling, resource lifetime, and whole-buildfile validity are outside scope. Unknown syntax is not labeled a QNX syntax error. [Technical scope and primary references](docs/technical-scope.md).

## Check and package

```sh
sh scripts/verify.sh
python3 scripts/package.py
```

The verification suite covers ordering, finite-wait caveats, foreground lifecycle assumptions, contract cycles, modifier inheritance, ambiguity, unknown syntax, bounded/invalid input, no source execution, output collision protection, comparison multiplicity, and HTML escaping. The ZIP contains source, fixtures, docs and tests; it excludes generated output and SDK material. There is no CI workflow or remote test claim.

With neither output option, the CLI prints JSON. Exit `0` means analysis completed, `2` means an input/output failure. Optional `--fail-on error` or `--fail-on warning` exits `1` when that review threshold is met. It is a review gate, not a QNX build acceptance gate.

## Competition and provenance

Prepared on 2026-11-09 for the QNX Global Hackathon's **Developer Tooling & Host Tools** category. Official rules accept tools running on a host that analyze or support software targeting QNX 8.0. The QNX-specific functionality here is the startup-script interpretation and resource-order model, demonstrated by reproducible local outputs. No official registration, submission, SDK execution or QNX boot is claimed. The 151.6-second edited CLI walkthrough with English narration/captions was rendered and decoded locally, then [published publicly on YouTube](https://youtu.be/K55o50_Tus4) on 2026-11-10; see its [media record](docs/local-demo-20261109.json). Anonymous playback has not been independently verified. The QNX registration form is filled, but Register has not been clicked and the entrant's confirmation of the rules is pending. [Rules and remaining submission material](docs/competition.md), [submission draft](docs/submission-draft.md), [under-three-minute recording script](docs/demo-script.md).

Buildfile editing and validation already exist. [Landscape](docs/landscape.md) compares `qnx-buildfile-lang` and S-CORE toolchains at fixed commits. Atlas is independently implemented; it does not copy their code or claim to replace their full parsers, IDE support or licensed build tools. AI coding assistance was used; the behavior is deterministic and contains no LLM runtime. MIT; see [third-party notices](THIRD_PARTY_NOTICES.md).

中文：这是面向 QNX 8 启动脚本的本地主机审查工具。服务依赖来自明确契约；等待只代表条件性路径检查。没有运行 QNX、申请 SDK 授权或完成官方投稿。
