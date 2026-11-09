"""Conservative line-oriented reader, NOT a replacement for mkifs."""

import re
import shlex

MAX_SOURCE_BYTES = 1_048_576
MAX_LINES = 20_000
MAX_EVENTS = 2_000


def diagnostic(code, message, line=None, *, severity="warning", **fields):
    return {"code": code, "severity": severity, "line": line, "message": message, **fields}


def uncomment(line):
    quoted, escaped = None, False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quoted:
            if char == quoted:
                quoted = None
        elif char in "\"'":
            quoted = char
        elif char == "#":
            return line[:i].strip()
    return line.strip()


def attributes(text):
    """Separate leading bracket groups without swallowing quoted closing brackets."""
    groups = []
    rest = text.strip()
    while rest.startswith("["):
        quote, escape, close = None, False, None
        for i, char in enumerate(rest[1:], 1):
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == "]":
                close = i
                break
        if close is None:
            raise ValueError("Unclosed attribute group")
        groups.extend(shlex.split(rest[1:close], posix=True))
        rest = rest[close + 1:].strip()
    return groups, rest


def _modifiers(tokens, inherited):
    result = dict(inherited)
    for token in tokens:
        if token in ("+external", "-external"):
            result["external"] = token[0] == "+"
        elif token in ("+critical", "-critical", "+session", "-session"):
            result[token[1:]] = token[0] == "+"
        elif re.fullmatch(r"(?:argv0|cpu|pri)=\S+", token):
            name, value = token.split("=", 1)
            result[name] = value
        else:
            result["unsupported"] = True
    return result


def parse_buildfile(text):
    if not isinstance(text, str):
        raise ValueError("Buildfile must be UTF-8 text")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("Buildfile must be UTF-8 text") from exc
    if any((ord(c) < 32 and c not in "\t\r\n") or ord(c) == 127 or c in "\x85\u2028\u2029" for c in text):
        raise ValueError("Unsupported control character or non-LF/CRLF line separator")
    if "\r" in text.replace("\r\n", ""):
        raise ValueError("Use LF or CRLF source lines; bare CR is unsupported")
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if size > MAX_SOURCE_BYTES or len(lines) > MAX_LINES:
        raise ValueError("Buildfile exceeds 1 MiB / 20,000 lines")
    events, issues, blocks = [], [], []
    current, default_script = None, False
    # Multiple +script files are concatenated by mkifs: modifiers carry forward.
    defaults = {"external": False}
    for number, original in enumerate(lines, 1):
        raw = uncomment(original)
        if not raw:
            continue
        if current is not None:
            if raw == "}":
                current = None
                continue
            if not current["script"]:
                continue
            event = {"line": number, "script": current["name"], "raw": original,
                     "kind": "unknown", "argv": [], "background": False, "modifiers": {}}
            events.append(event)
            if len(events) > MAX_EVENTS:
                raise ValueError("Buildfile exceeds 2,000 script events")
            try:
                attrs, command = attributes(raw)
                mods = _modifiers(attrs, defaults)
                event["modifiers"] = mods
                if not command:
                    defaults = mods
                    event["kind"] = "modifier"
                    if mods.get("unsupported"):
                        raise ValueError("Unrecognized inherited modifier")
                    continue
                if mods.get("unsupported"):
                    raise ValueError("Unrecognized modifier affects this command")
                # Expansion and escaped inline characters need a full mkifs parser.
                # Refuse to manufacture literal dependency paths from them.
                if any(c in command for c in "\\$`{}"):
                    raise ValueError("Expansion, inline escaping, or continuation is outside this reader")
                lexer = shlex.shlex(command, posix=True, punctuation_chars="&|;<>()")
                lexer.whitespace_split = True
                lexer.commenters = ""
                argv = list(lexer)
                if argv and argv[-1] == "&":
                    event["background"] = True
                    argv.pop()
                if not argv or any(any(c in token for c in "&|;<>()*?") for token in argv):
                    raise ValueError("Shell operators, globbing, or empty commands are outside this reader")
                env = []
                while argv and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[0]):
                    env.append(argv.pop(0))
                event["environment"] = env
                event["argv"] = argv
                if not argv:
                    event["kind"] = "environment"
                elif argv[0] in ("sh", "ksh", "bash", "/bin/sh", "/bin/ksh", "/bin/bash"):
                    raise ValueError("An explicit shell is an analysis boundary")
                elif argv[0] in ("waitfor", "reopen", "procmgr_symlink", "display_msg") and not mods["external"]:
                    event["kind"] = argv[0]
                else:
                    event["kind"] = "launch"
            except ValueError as exc:
                event["kind"] = "unknown"
                issues.append(diagnostic("UNSUPPORTED_SCRIPT", str(exc), number, coverage_gap=True))
            continue
        try:
            attrs, rest = attributes(raw)
        except ValueError:
            issues.append(diagnostic("UNSUPPORTED_BUILD_LINE", "Cannot delimit buildfile attributes", number,
                                     coverage_gap=True))
            continue
        if any(attr.startswith(("filter=", "patch=")) for attr in attrs):
            issues.append(diagnostic("BUILD_TRANSFORM_UNMODELED", "Build-time transform is not evaluated", number,
                                     coverage_gap=True))
        script = default_script
        for attr in attrs:
            if attr == "+script":
                script = True
            elif attr == "-script":
                script = False
        if not rest:
            default_script = script
            continue
        if rest.endswith("{") and "=" in rest:
            name = rest.rsplit("=", 1)[0].strip()
            current = {"name": name, "script": script, "line": number}
            if script:
                blocks.append(dict(current))
        elif script:
            issues.append(diagnostic("EXTERNAL_SCRIPT", "External or non-multiline script not read; supply an inline review copy", number,
                                     coverage_gap=True))
        elif "{" in rest or "}" in rest or rest.startswith(("include", "#include")):
            issues.append(diagnostic("UNSUPPORTED_BUILD_LINE", "Buildfile construct not interpreted", number,
                                     coverage_gap=True))
    if current is not None:
        issues.append(diagnostic("UNTERMINATED_INLINE", "Inline block not closed in the supplied review text", current["line"],
                                 coverage_gap=True))
    if not blocks:
        issues.append(diagnostic("NO_INLINE_SCRIPT", "No supported inline +script block found", coverage_gap=True))
    return {"events": events, "diagnostics": issues, "script_blocks": blocks,
            "source_lines": lines, "source_bytes": size}
