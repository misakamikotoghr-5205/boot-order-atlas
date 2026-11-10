# Submission copy · not submitted

**English title:** Boot Order Atlas — Review QNX 8 Startup Dependencies Before the First Boot

**中文标题：** Boot Order Atlas：在首次启动前审阅 QNX 8 启动依赖

**Tagline:** Review QNX 8 startup dependencies, conditional waits and revision risks with source-linked diagnostics and offline reports.

## English summary

QNX startup scripts can launch resource managers asynchronously while later programs assume their paths already exist. A text diff shows changed lines but leaves the reviewer to reconstruct the startup order and the assumptions behind each dependency.

Boot Order Atlas reads a supported subset of QNX SDP 8.0 `mkifs` inline startup scripts and an explicit service/resource contract. It reports consumers placed before declared producers, missing conditional path waits, foreground return risks, ambiguous resource ownership and contract dependency cycles. Every event and diagnostic links back to source lines. Version review distinguishes event changes, line movements and diagnostic changes, while preserving source and contract fingerprints.

The implementation is a dependency-free Python host CLI with JSON and self-contained HTML artifacts. It does not execute source or QNX tooling. Included original fixtures demonstrate the tool's behavior with fictional service declarations. A `waitfor` is always presented as a finite `stat()` check that can time out, never as proof of service health. Unsupported syntax stays visible as a coverage gap.

## 中文摘要

QNX 启动脚本常在后台启动资源管理器；后续应用却可能在设备路径出现前启动。普通文本差异难以直接呈现这些顺序和依赖假设。

Boot Order Atlas 将 QNX 8 `mkifs` 内联启动脚本与显式服务契约对齐，逐行展示提供者尚未启动、缺少路径等待、前台阻塞风险、提供者歧义及契约循环，并比较修订前后的指令和诊断变化。它输出可离线审阅的 JSON 和单文件 HTML。

该工具在主机本地运行，采用 Python 标准库，不执行脚本、不访问设备、不假称实际启动了 QNX。示例服务是明确标注的虚构输入。等待屏障仅表示可能超时的路径检查；未知语法会保留为分析缺口。

## Technology / QNX support

Python 3.10+, `argparse`, strict JSON declarations, a bounded conservative script reader, dependency SCC analysis, source/contract SHA-256 and escaped static HTML. The QNX-specific implementation distinguishes `+script`, modifier scope, `+external`, background launch, internal `waitfor`/`reopen` and `procmgr_symlink`. No SDK or target toolchain is used. Intended runtime: a host with Python, locally verified on Linux; other supported Python host platforms have not been exercised here.

## Difference from existing work

QNX buildfile editing/parsing/validation already exist, including `qnx-buildfile-lang`. Atlas's implemented focus is a reviewable startup-resource contract and before/after artifact. Its parser is narrower and it complements, rather than replaces, full validation or an actual licensed build. Two primary OSS comparisons with fixed commits/licenses are recorded in `docs/landscape.md`.

## Build process / AI and OSS disclosure

Built on 2026-11-09 after reading official QNX 8 syntax and the host-tool competition rules. AI coding assistance (Codex) was used for implementation, documentation and tests. An independent agent reviewed semantics and reproduced Unicode line-separator and stale-guard defects; both received regression fixes. This is a deterministic program with no model/runtime API or fabricated target logs. No third-party implementation code was copied. Original implementation and fixtures are MIT; referenced OSS licenses remain with their owners.

## Prepared links and remaining entry work

- Public source repository: https://github.com/misakamikotoghr-5205/boot-order-atlas
- Public YouTube demonstration: https://youtu.be/K55o50_Tus4 — published 2026-11-10; the original 151.6-second video is an edited host CLI walkthrough. Anonymous playback has not been independently verified.

On November 10, official registration was confirmed by "Thanks for registering!" and My hackathon projects showing 0. Project creation is in progress; no new project creation or final submission is confirmed. The current status is `registered_entry_in_progress`; final entry preparation and submission remain outstanding. Do not substitute a script, screenshot, simulated boot or local path for the required entry fields. The README's local commands and the demo script are ready to use; publishing the video does not establish registration or a final-entry receipt.
