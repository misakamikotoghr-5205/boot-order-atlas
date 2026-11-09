"""Self-contained, script-free and HTML-escaped review artifacts."""

import html
import json


def _e(value):
    return html.escape(str(value), quote=True)


def _analysis(report, prefix):
    summary = report["summary"]
    rows = []
    for item in report["diagnostics"]:
        line = item["line"]
        location = f'<a href="#{prefix}-L{line}">L{line}</a>' if line else "contract"
        context = " · ".join(str(item[k]) for k in ("service", "resource", "services") if k in item)
        rows.append(f'<tr><td class="{_e(item["severity"])}">{_e(item["severity"])}</td>'
                    f'<td>{location}</td><td><strong>{_e(item["code"])}</strong><br>{_e(item["message"])}'
                    f'<br><small>{_e(context)}</small></td></tr>')
    timeline = []
    for event in report["events"]:
        details = []
        if event.get("wait"):
            details.append("stat wait " + event["wait"]["resource"] + " ≤ " + event["wait"]["seconds"] + " s; may time out")
        for requirement in event.get("requirements", []):
            details.append(requirement["resource"] + ": " + requirement["status"])
        timeline.append(f'<li><a href="#{prefix}-L{event["line"]}">L{event["line"]}</a> '
                        f'<strong>{_e(event["service"] or event["kind"])}</strong> '
                        f'<code>{_e(" ".join(event["argv"]))}{" &amp;" if event["background"] else ""}</code>'
                        f'<small>{_e(event["reachability"])} · {_e("; ".join(details))}</small></li>')
    edges = "".join(f'<li>{_e(e["provider"])} → {_e(e["consumer"])} <code>{_e(e["resource"])}</code></li>'
                    for e in report["dependency_edges"])
    source = "\n".join(f'<span id="{prefix}-L{i}"><b>{i:4}</b> {_e(line)}</span>'
                       for i, line in enumerate(report["source"]["lines"], 1))
    caveats = "".join(f'<li>{_e(c)}</li>' for c in report["caveats"])
    return f'''<section><h2>{_e(report['source']['name'])}</h2>
<p class="hash">Source SHA-256 {_e(report['source']['sha256'])}<br>Contract SHA-256 {_e(report['contract_sha256'])}</p>
<div class="stats"><strong>{_e(summary['status'])}</strong><span>{summary['events']} events</span>
<span>{summary['matched_launches']} matched launches</span><span>{summary['error']} contract errors</span>
<span>{summary['warning']} review warnings</span><span>{summary['coverage_gaps']} coverage gaps</span></div>
<h3>Review timeline</h3><ol class="timeline">{''.join(timeline) or '<li>No supported script events</li>'}</ol>
<h3>Declared resource edges</h3><ul>{edges or '<li>No declared edges</li>'}</ul>
<h3>Diagnostics</h3><table><thead><tr><th>Level</th><th>Source</th><th>Finding</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="3">No model diagnostics; runtime remains unproven.</td></tr>'}</tbody></table>
<h3>Limits and assumptions</h3><ul>{caveats}</ul>
<details><summary>Contract declarations</summary><pre>{_e(json.dumps(report['contract'], indent=2, ensure_ascii=False))}</pre></details>
<details open><summary>Source with line references</summary><pre class="source">{source}</pre></details></section>'''


def render_html(value):
    if value["schema"] == "boot-order-atlas.report/v1":
        body = _analysis(value, "source")
    elif value["schema"] == "boot-order-atlas.comparison/v1":
        introduced = "".join(f'<li>{_e(d["code"])} — {_e(d["message"])}</li>' for d in value["introduced_diagnostics"])
        removed = "".join(f'<li>{_e(d["code"])} — {_e(d["message"])}</li>' for d in value["no_longer_reported"])
        body = f'''<section><h2>Version review</h2><p>{_e(value['caveat'])}</p>
<p>{len(value['event_changes'])} event change groups · {len(value['line_moves'])} unchanged events moved · Contract changed: {_e(value['contract_changed'])}</p>
<h3>Introduced diagnostics</h3><ul>{introduced or '<li>None</li>'}</ul>
<h3>No longer reported</h3><ul>{removed or '<li>None</li>'}</ul>
<h3>Source diff</h3><pre>{_e(chr(10).join(value['source_diff']))}</pre></section>'''
        body += _analysis(value["before"], "before") + _analysis(value["after"], "after")
    else:
        raise ValueError("Unsupported report schema")
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Boot Order Atlas · QNX 8 startup review</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101721;color:#e5edf5;font:16px/1.6 system-ui,sans-serif}
main{max-width:1160px;margin:auto;padding:40px 24px}header{border-bottom:1px solid #34475b;padding-bottom:24px}h1{font-size:40px;line-height:1.15;margin:0 0 12px}h2{font-size:26px}h3{margin-top:28px}p{max-width:90ch}a{color:#8cdbd0}section{margin:30px 0;padding:24px;background:#182331;border:1px solid #34475b;border-radius:12px}.badge{color:#8cdbd0;font-weight:700;letter-spacing:.08em}.hash{font:12px/1.8 monospace;overflow-wrap:anywhere;color:#a6b9ca}.stats{display:flex;flex-wrap:wrap;gap:10px}.stats>*{padding:8px 12px;background:#223345;border-radius:6px}.timeline{padding-left:30px}.timeline li{padding:10px 0;border-bottom:1px solid #34475b}.timeline small{display:block;color:#b6c7d7}code,pre{font-family:ui-monospace,monospace}pre{background:#101721;padding:14px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}code{color:#b5e0b6}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #34475b;padding:10px}th{color:#adc1d4}.error{color:#ffb5b0}.warning{color:#ffd38a}.info{color:#8cdbd0}small{color:#adc1d4}.source span{display:block;scroll-margin-top:20px}.source span:target{background:#3f472d}.source b{color:#8299af}summary{cursor:pointer;margin:18px 0;font-weight:600}@media(max-width:600px){main{padding:24px 12px}section{padding:14px}h1{font-size:30px}td,th{padding:6px}}
</style></head><body><main><header><p class="badge">HOST REVIEW / QNX SDP 8.0</p><h1>Boot Order Atlas</h1>
<p>Review startup order, conditional path waits and declared resource dependencies. This is a static host report, not an observed QNX boot or a safety certification.</p></header>''' + body + '</main></body></html>\n'
