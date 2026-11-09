import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .analysis import analyze_text, compare_reports
from .contract import MAX_CONTRACT_BYTES, load_contract
from .parser import MAX_SOURCE_BYTES
from .report import render_html


def _read(path, limit):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Input exceeds the documented size limit: " + Path(path).name)
    return raw.decode("utf-8")


def _write(path, content):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent,
                                         prefix=".atlas-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="QNX 8 inline mkifs startup review; never executes source or SDK tools")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("analyze", "compare"):
        sub = commands.add_parser(command)
        if command == "analyze":
            sub.add_argument("buildfile")
        else:
            sub.add_argument("before")
            sub.add_argument("after")
            sub.add_argument("--before-contract", help="defaults to --contract; contract changes are flagged")
        sub.add_argument("--contract", required=True, help="explicit service/resource declarations JSON")
        sub.add_argument("--json", dest="json_path", help="write machine-readable report")
        sub.add_argument("--html", dest="html_path", help="write self-contained HTML report")
        sub.add_argument("--fail-on", choices=("never", "error", "warning"), default="never",
                         help="optional review gate; does not validate QNX syntax/runtime")
    args = parser.parse_args(argv)
    try:
        inputs = [args.contract]
        inputs += [args.buildfile] if args.command == "analyze" else [args.before, args.after]
        if args.command == "compare" and args.before_contract:
            inputs.append(args.before_contract)
        destinations = [p for p in (args.json_path, args.html_path) if p]
        resolved = [Path(p).resolve() for p in destinations]
        if len(set(resolved)) != len(resolved) or any(p in {Path(i).resolve() for i in inputs} for p in resolved):
            raise ValueError("Report outputs must be distinct from each other and every input")
        contract = load_contract(_read(args.contract, MAX_CONTRACT_BYTES))
        if args.command == "analyze":
            report = analyze_text(_read(args.buildfile, MAX_SOURCE_BYTES), contract, Path(args.buildfile).name)
            latest = report
        else:
            earlier = load_contract(_read(args.before_contract, MAX_CONTRACT_BYTES)) if args.before_contract else contract
            before = analyze_text(_read(args.before, MAX_SOURCE_BYTES), earlier, Path(args.before).name)
            after = analyze_text(_read(args.after, MAX_SOURCE_BYTES), contract, Path(args.after).name)
            report = compare_reports(before, after)
            latest = after
        encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.json_path:
            _write(args.json_path, encoded)
        if args.html_path:
            _write(args.html_path, render_html(report))
        if not destinations:
            sys.stdout.write(encoded)
        else:
            summary = latest["summary"]
            print(f"{summary['status']}: {summary['error']} contract errors, {summary['warning']} review warnings, "
                  f"{summary['coverage_gaps']} coverage gaps. No QNX execution performed.")
        gated = args.fail_on != "never" and (latest["summary"]["error"] or
                  (args.fail_on == "warning" and latest["summary"]["warning"]))
        return 1 if gated else 0
    except (OSError, ValueError, RecursionError) as exc:
        print("Input/output error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
