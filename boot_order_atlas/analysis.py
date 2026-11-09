"""Contract-relative review. No target execution, filesystem probing, or SDK calls."""

import difflib
from collections import defaultdict
import hashlib
import json
import posixpath
import re

from .contract import validate_contract
from .parser import diagnostic, parse_buildfile

REPORT_SCHEMA = "boot-order-atlas.report/v1"


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _path(value):
    return (value.startswith("/") and value == posixpath.normpath(value) and
            not value.startswith("//") and not any(c in value for c in "$*?[]{}\\"))


def _cycles(nodes, edges):
    """Deterministic Tarjan SCCs; bounded to 128 declared services."""
    graph = {node: [] for node in nodes}
    for edge in edges:
        graph[edge["provider"]].append(edge["consumer"])
    stack, active, index, low, groups = [], set(), {}, {}, []

    def visit(node):
        index[node] = low[node] = len(index)
        stack.append(node)
        active.add(node)
        for child in sorted(set(graph[node])):
            if child not in index:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in active:
                low[node] = min(low[node], index[child])
        if low[node] == index[node]:
            group = []
            while True:
                child = stack.pop()
                active.remove(child)
                group.append(child)
                if child == node:
                    break
            if len(group) > 1 or node in graph[node]:
                groups.append(sorted(group))

    for node in sorted(nodes):
        if node not in index:
            visit(node)
    return sorted(groups)


def analyze_text(text, contract, source_name="buildfile.build"):
    """Analyze inline startup scripts under explicit assumptions; return JSON data.

    Diagnostics never establish actual QNX acceptance, resource health, boot
    success, or a deadline guarantee. A waitfor is only a conditional stat barrier.
    """
    contract = validate_contract(contract)
    parsed = parse_buildfile(text)
    events, issues = parsed["events"], parsed["diagnostics"]
    services = {item["id"]: item for item in contract["services"]}
    providers = {}
    for service in contract["services"]:
        for resource in service["provides"]:
            providers.setdefault(resource, []).append(service["id"])
    launches = {sid: [] for sid in services}
    for number, event in enumerate(events):
        event["sequence"] = number + 1
        event["service"] = None
        if event["kind"] != "launch":
            continue
        argv = event["argv"]
        matches = [s for s in contract["services"] if argv[:len(s["argv_prefix"])] == s["argv_prefix"]]
        if len(matches) == 1:
            event["service"] = matches[0]["id"]
            launches[matches[0]["id"]].append(number)
        elif len(matches) > 1:
            issues.append(diagnostic("AMBIGUOUS_SERVICE", "Command matches multiple contract declarations", event["line"],
                                     services=sorted(s["id"] for s in matches), coverage_gap=True))
        else:
            issues.append(diagnostic("UNMODELED_COMMAND", "Executable behavior is not declared in the contract", event["line"],
                                     command=argv[0], coverage_gap=True))

    initial = set(contract["initial_resources"])
    dependencies = []
    for consumer in contract["services"]:
        for resource in consumer["requires"]:
            if resource in initial:
                continue
            for provider in providers.get(resource, []):
                dependencies.append({"provider": provider, "consumer": consumer["id"], "resource": resource})
    # Only a unique provider establishes a dependency edge for cycle claims.
    unique_edges = [e for e in dependencies if len(providers[e["resource"]]) == 1]
    cycles = _cycles(services, unique_edges)
    for group in cycles:
        issues.append(diagnostic("CONTRACT_CYCLE", "Declared before-launch dependencies form a cycle; not a runtime deadlock proof",
                                 services=group, severity="error"))
    for sid, indices in launches.items():
        if not indices:
            issues.append(diagnostic("SERVICE_NOT_LAUNCHED", "Declared service has no uniquely matched launch", service=sid))
        if len(indices) > 1:
            issues.append(diagnostic("REPEATED_SERVICE", "Multiple launches share one service declaration; review lifecycle assumptions",
                                     events[indices[1]]["line"], service=sid))
    for resource, ids in sorted(providers.items()):
        if len(ids) > 1:
            issues.append(diagnostic("AMBIGUOUS_PROVIDER", "Several services declare this resource; no single producer is inferred",
                                     resource=resource, services=sorted(ids)))

    guards, blocked_at, uncertain_at = {}, None, None
    for i, event in enumerate(events):
        event["reachability"] = ("blocked_under_contract" if blocked_at else
                                  "unproven_after_foreground" if uncertain_at else "ordered_under_contract")
        if blocked_at:
            event["blocked_by_line"] = blocked_at
            issues.append(diagnostic("AFTER_BLOCKING_FOREGROUND", "Earlier foreground command is declared not to return",
                                     event["line"], blocking_line=blocked_at, severity="error"))
        elif uncertain_at:
            event["uncertain_after_line"] = uncertain_at
        kind, argv = event["kind"], event["argv"]
        if kind in ("waitfor", "reopen"):
            args = argv[1:]
            if kind == "reopen" and not args:
                args = ["/dev/console"]
            valid = (not event["background"] and 1 <= len(args) <= 2 and _path(args[0]) and
                     (len(args) == 1 or bool(re.fullmatch(r"[0-9]+(?:\.[0-9])?", args[1]))))
            if not valid:
                issues.append(diagnostic("UNSUPPORTED_WAIT", "Only internal literal path [seconds] waits are modeled; no polling argument",
                                         event["line"], coverage_gap=True))
                continue
            resource = args[0]
            prior_ids = sorted(sid for sid in providers.get(resource, []) if any(x < i for x in launches[sid]))
            event["wait"] = {"resource": resource, "seconds": args[1] if len(args) == 2 else "5.0",
                             "condition": "stat_success_or_timeout", "prior_providers": prior_ids}
            if blocked_at is None:
                guards[resource] = {"line": event["line"], "sequence": i, "prior_providers": prior_ids,
                                    "reachability": event["reachability"]}
            if resource not in initial and not prior_ids:
                future = sorted(sid for sid in providers.get(resource, []) if any(x > i for x in launches[sid]))
                code = "WAIT_BEFORE_PROVIDER" if future else "WAIT_WITHOUT_PROVIDER"
                issues.append(diagnostic(code, "Wait has no earlier declared provider; it can expire before any modeled producer starts",
                                         event["line"], resource=resource, services=future))
            issues.append(diagnostic("WAIT_MAY_TIMEOUT", "Finite stat wait does not prove service health or stop later commands on failure",
                                     event["line"], resource=resource, severity="info"))
        elif kind == "procmgr_symlink":
            if len(argv) == 3 and not event["background"]:
                event["symlink"] = {"source": argv[1], "link": argv[2]}
                issues.append(diagnostic("SYMLINK_NOT_READINESS", "Link creation is recorded; target existence and path-prefix resolution are not inferred",
                                         event["line"], severity="info"))
            else:
                issues.append(diagnostic("UNSUPPORTED_SYMLINK", "Cannot model this procmgr_symlink invocation", event["line"],
                                         coverage_gap=True))
        elif kind == "launch":
            sid = event["service"]
            event["requirements"] = []
            if sid:
                service = services[sid]
                for resource in service["requires"]:
                    ids = providers.get(resource, [])
                    earlier = [s for s in ids if any(x < i for x in launches[s])]
                    guard = guards.get(resource)
                    state = "unproven"
                    if resource in initial:
                        state = "declared_initial"
                    elif len(ids) > 1:
                        issues.append(diagnostic("RESOURCE_PROVIDER_AMBIGUOUS", "Cannot select one declared provider", event["line"],
                                                 service=sid, resource=resource))
                    elif not ids:
                        issues.append(diagnostic("RESOURCE_UNMODELED", "No provider or initial resource is declared; an external source may exist",
                                                 event["line"], service=sid, resource=resource, coverage_gap=True))
                    elif not earlier:
                        issues.append(diagnostic("PROVIDER_NOT_STARTED", "Required resource has no earlier declared provider launch",
                                                 event["line"], service=sid, resource=resource, services=ids))
                    elif (guard and guard["prior_providers"] and guard["reachability"] == "ordered_under_contract" and
                          event["reachability"] == "ordered_under_contract"):
                        state = "conditional_stat_barrier"
                    else:
                        issues.append(diagnostic("RESOURCE_UNGUARDED", "Provider launch precedes consumer, but no reachable subsequent stat barrier is present",
                                                 event["line"], service=sid, resource=resource))
                    event["requirements"].append({"resource": resource, "status": state,
                                                   "guard_line": guard["line"] if guard else None})
                if not event["background"] and not blocked_at:
                    if service["foreground"] == "blocks":
                        blocked_at = event["line"]
                        issues.append(diagnostic("BLOCKING_FOREGROUND", "Contract declares this foreground invocation does not return",
                                                 event["line"], service=sid, severity="error"))
                    elif service["foreground"] == "unknown":
                        uncertain_at = uncertain_at or event["line"]
                        issues.append(diagnostic("FOREGROUND_RETURN_UNKNOWN", "Later execution depends on this undeclared return behavior",
                                                 event["line"], service=sid))
            elif not event["background"]:
                uncertain_at = uncertain_at or event["line"]
        elif kind == "unknown":
            # Unsupported lines may alter execution or resources. Do not promote
            # later guards to a fully ordered conditional barrier.
            uncertain_at = uncertain_at or event["line"]

    issues.sort(key=lambda d: (d["line"] or 0, d["code"], d.get("service", ""), d.get("resource", "")))
    gaps = sum(bool(d.get("coverage_gap")) for d in issues)
    counts = {level: sum(d["severity"] == level for d in issues) for level in ("error", "warning", "info")}
    return {"schema": REPORT_SCHEMA, "tool_version": "0.1.0", "qnx_documentation_version": "8.0",
            "source": {"name": posixpath.basename(source_name.replace("\\", "/")), "sha256": _digest(text),
                       "bytes": parsed["source_bytes"], "lines": parsed["source_lines"]},
            "contract": contract, "contract_sha256": _digest(_canonical(contract)),
            "scope": {"kind": "host_static_review", "target_executed": False, "sdk_used": False,
                      "image_validated": False, "runtime_readiness_proven": False},
            "summary": {"status": "review_required" if counts["error"] or counts["warning"] else "modeled_with_caveats",
                        "events": len(events), "inline_scripts": len(parsed["script_blocks"]),
                        "matched_launches": sum(e["service"] is not None for e in events),
                        "coverage_gaps": gaps, **counts},
            "script_blocks": parsed["script_blocks"], "events": events,
            "dependency_edges": dependencies, "contract_cycles": cycles, "diagnostics": issues,
            "caveats": ["All service behavior and initial resources are user declarations, not verified facts.",
                        "Finite waitfor/reopen checks stat only; timeout, crashes, restarts, health and timing remain unproven.",
                        "Image layout, binaries, libraries, permissions, includes, executable availability and QNX syntax acceptance are not validated.",
                        "Unknown syntax is a coverage gap, not a claim that QNX rejects the buildfile."]}


def _event_key(event):
    fields = {k: event.get(k) for k in ("kind", "argv", "background", "modifiers", "service", "wait", "environment")}
    if event["kind"] == "unknown":
        fields["uninterpreted_source"] = event["raw"]
    return _canonical(fields)


def _diagnostic_key(item):
    return _canonical({k: value for k, value in item.items() if k not in ("line", "blocking_line")})


def compare_reports(before, after):
    """Compare locally generated reports. No inference that a resolved warning is a runtime fix."""
    if any(not isinstance(r, dict) or r.get("schema") != REPORT_SCHEMA for r in (before, after)):
        raise ValueError("compare_reports requires two generated report/v1 objects")
    old, new = before["events"], after["events"]
    matcher = difflib.SequenceMatcher(a=[_event_key(e) for e in old], b=[_event_key(e) for e in new], autojunk=False)
    changes, moved = [], []
    for op, a, b, c, d in matcher.get_opcodes():
        if op == "equal":
            for left, right in zip(old[a:b], new[c:d]):
                if left["line"] != right["line"]:
                    moved.append({"before_line": left["line"], "after_line": right["line"], "argv": right["argv"]})
        else:
            changes.append({"kind": op, "before": old[a:b], "after": new[c:d]})
    old_diags, new_diags = defaultdict(list), defaultdict(list)
    for item in before["diagnostics"]:
        old_diags[_diagnostic_key(item)].append(item)
    for item in after["diagnostics"]:
        new_diags[_diagnostic_key(item)].append(item)
    return {"schema": "boot-order-atlas.comparison/v1", "tool_version": "0.1.0",
            "before": before, "after": after,
            "contract_changed": before["contract_sha256"] != after["contract_sha256"],
            "event_changes": changes, "line_moves": moved,
            "introduced_diagnostics": [item for k in sorted(new_diags) for item in new_diags[k][len(old_diags[k]):]],
            "no_longer_reported": [item for k in sorted(old_diags) for item in old_diags[k][len(new_diags[k]):]],
            "source_diff": list(difflib.unified_diff(before["source"]["lines"], after["source"]["lines"],
                                                      fromfile=before["source"]["name"], tofile=after["source"]["name"], lineterm="")),
            "caveat": "Diagnostic changes reflect this static model and its contract, not observed boot fixes."}
