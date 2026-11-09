import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from boot_order_atlas import analyze_text, compare_reports, load_contract, validate_contract
from boot_order_atlas.parser import parse_buildfile
from boot_order_atlas.report import render_html

ROOT = Path(__file__).resolve().parents[1]


def declaration(sid, command=None, provides=(), requires=(), foreground="blocks"):
    return {"id": sid, "argv_prefix": [command or sid], "provides": list(provides),
            "requires": list(requires), "foreground": foreground}


def contract(*services, initial=()):
    return {"schema": "boot-order-atlas.contract/v1", "initial_resources": list(initial), "services": list(services)}


def build(*lines):
    return "[+script] .script = {\n" + "\n".join(lines) + "\n}\n"


def codes(report):
    return {item["code"] for item in report["diagnostics"]}


class OrderReviewTests(unittest.TestCase):
    def setUp(self):
        self.model = contract(declaration("driver", provides=["/dev/console"]),
                              declaration("client", requires=["/dev/console"]))

    def test_example_change_adds_barriers_without_claiming_health(self):
        model = load_contract((ROOT / "examples/serial-contract.json").read_text())
        before = analyze_text((ROOT / "examples/serial-before.build").read_text(), model)
        after = analyze_text((ROOT / "examples/serial-after.build").read_text(), model)
        self.assertIn("RESOURCE_UNGUARDED", codes(before))
        self.assertNotIn("RESOURCE_UNGUARDED", codes(after))
        self.assertEqual(after["summary"]["status"], "modeled_with_caveats")
        self.assertFalse(after["scope"]["runtime_readiness_proven"])
        panel = next(e for e in after["events"] if e["service"] == "panel")
        self.assertEqual([r["status"] for r in panel["requirements"]], ["conditional_stat_barrier"] * 2)
        self.assertEqual(len([d for d in after["diagnostics"] if d["code"] == "WAIT_MAY_TIMEOUT"]), 3)

    def test_future_provider_does_not_satisfy_consumer(self):
        report = analyze_text(build("client &", "driver &"), self.model)
        self.assertIn("PROVIDER_NOT_STARTED", codes(report))

    def test_wait_before_launch_cannot_guard_later_consumer(self):
        report = analyze_text(build("waitfor /dev/console", "driver &", "client &"), self.model)
        self.assertTrue({"WAIT_BEFORE_PROVIDER", "RESOURCE_UNGUARDED"} <= codes(report))

    def test_wait_for_unknown_resource_is_not_declared_failure_of_qnx(self):
        report = analyze_text(build("waitfor /dev/missing", "client &"), contract(declaration("client", requires=["/dev/missing"])))
        self.assertTrue({"WAIT_WITHOUT_PROVIDER", "RESOURCE_UNMODELED"} <= codes(report))
        self.assertGreater(report["summary"]["coverage_gaps"], 0)

    def test_declared_initial_resource_breaks_dependency_need(self):
        report = analyze_text(build("client &"), contract(declaration("client", requires=["/dev/console"]), initial=["/dev/console"]))
        self.assertEqual(report["events"][0]["requirements"][0]["status"], "declared_initial")
        self.assertFalse(report["dependency_edges"])

    def test_foreground_blocker_marks_later_events_unreachable_under_contract(self):
        report = analyze_text(build("driver", "waitfor /dev/console", "client &"), self.model)
        self.assertIn("BLOCKING_FOREGROUND", codes(report))
        self.assertEqual(report["events"][2]["reachability"], "blocked_under_contract")
        self.assertNotEqual(report["events"][2]["requirements"][0]["status"], "conditional_stat_barrier")

    def test_returning_foreground_is_not_resource_readiness(self):
        model = copy.deepcopy(self.model)
        model["services"][0]["foreground"] = "returns"
        report = analyze_text(build("driver", "client &"), model)
        self.assertIn("RESOURCE_UNGUARDED", codes(report))
        self.assertNotIn("BLOCKING_FOREGROUND", codes(report))

    def test_unknown_foreground_makes_later_guard_unproven(self):
        report = analyze_text(build("mystery", "driver &", "waitfor /dev/console", "client &"), self.model)
        self.assertEqual(report["events"][-1]["reachability"], "unproven_after_foreground")
        self.assertIn("RESOURCE_UNGUARDED", codes(report))

    def test_earlier_guard_cannot_be_promoted_across_unknown_or_blocked_boundary(self):
        model = copy.deepcopy(self.model)
        model["services"].append(declaration("blocker"))
        for boundary in ('/bin/sh -c "rm /dev/console"', "blocker"):
            with self.subTest(boundary=boundary):
                report = analyze_text(build("driver &", "waitfor /dev/console", boundary, "client &"), model)
                self.assertEqual(report["events"][-1]["requirements"][0]["status"], "unproven")
                self.assertIn("RESOURCE_UNGUARDED", codes(report))

    def test_cycle_is_contract_relative_and_initial_resource_breaks_it(self):
        model = load_contract((ROOT / "examples/cycle-contract.json").read_text())
        source = (ROOT / "examples/cycle.build").read_text()
        report = analyze_text(source, model)
        self.assertEqual(report["contract_cycles"], [["a", "b"]])
        self.assertIn("CONTRACT_CYCLE", codes(report))
        model["initial_resources"] = ["/dev/workshop-b"]
        self.assertEqual(analyze_text(source, model)["contract_cycles"], [])

    def test_ambiguous_provider_does_not_invent_a_unique_dependency(self):
        model = contract(declaration("a", provides=["/dev/x"]), declaration("b", provides=["/dev/x"]),
                         declaration("c", requires=["/dev/x"]))
        report = analyze_text(build("a &", "b &", "waitfor /dev/x", "c &"), model)
        self.assertTrue({"AMBIGUOUS_PROVIDER", "RESOURCE_PROVIDER_AMBIGUOUS"} <= codes(report))
        self.assertEqual(report["events"][-1]["requirements"][0]["status"], "unproven")

    def test_overlapping_prefixes_and_repeated_service_are_explicit(self):
        model = contract(declaration("a", "same"), declaration("b", "same"))
        self.assertIn("AMBIGUOUS_SERVICE", codes(analyze_text(build("same &"), model)))
        self.assertIn("REPEATED_SERVICE", codes(analyze_text(build("driver &", "driver &"), self.model)))

    def test_contract_input_is_not_mutated_and_reports_are_reproducible(self):
        original = copy.deepcopy(self.model)
        first = analyze_text(build("driver &", "client &"), self.model)
        second = analyze_text(build("driver &", "client &"), self.model)
        self.assertEqual(first, second)
        first["contract"]["services"][0]["id"] = "changed"
        self.assertEqual(self.model, original)


class ParserBoundaryTests(unittest.TestCase):
    def test_modifier_scope_distinguishes_external_waitfor(self):
        parsed = parse_buildfile(build("[+external]", "waitfor /dev/a 1.0 100", "[-external] waitfor /dev/b", "waitfor /dev/c 1.0 100"))
        self.assertEqual([e["kind"] for e in parsed["events"]], ["modifier", "launch", "waitfor", "launch"])
        report = analyze_text(build("waitfor /dev/a 1.0 100"), contract())
        self.assertIn("UNSUPPORTED_WAIT", codes(report))

    def test_reopen_defaults_and_symlink_argument_order(self):
        report = analyze_text(build("reopen", "procmgr_symlink /source /link"), contract(initial=["/dev/console"]))
        self.assertEqual(report["events"][0]["wait"]["resource"], "/dev/console")
        self.assertEqual(report["events"][0]["wait"]["seconds"], "5.0")
        self.assertEqual(report["events"][1]["symlink"], {"source": "/source", "link": "/link"})
        self.assertIn("SYMLINK_NOT_READINESS", codes(report))

    def test_background_wait_is_not_promoted_to_barrier(self):
        report = analyze_text(build("waitfor /dev/a &"), contract())
        self.assertIn("UNSUPPORTED_WAIT", codes(report))
        self.assertNotIn("wait", report["events"][0])

    def test_plain_inline_data_and_bootstrap_are_not_startup_commands(self):
        text = '[virtual=x86_64,bios] .bootstrap = {\n startup-x86\n procnto-smp-instr\n}\n/etc/note = {\n waitfor /not/a/script\n}\n' + build("display_msg ready")
        report = analyze_text(text, contract())
        self.assertEqual(len(report["events"]), 1)
        self.assertEqual(report["events"][0]["kind"], "display_msg")

    def test_multiple_script_blocks_follow_buildfile_order_and_global_attribute(self):
        text = "[+script]\nfirst = {\n display_msg one\n}\nsecond = {\n display_msg two\n}\n[-script]\n/data = {\nignored\n}\n"
        report = analyze_text(text, contract())
        self.assertEqual([e["argv"][-1] for e in report["events"]], ["one", "two"])
        self.assertEqual(report["summary"]["inline_scripts"], 2)

    def test_env_assignments_are_not_executables_and_expansion_is_a_gap(self):
        report = analyze_text(build("PATH=/proc/boot", "TERM=qansi client &", "waitfor $DEVICE"), contract(declaration("client")))
        self.assertEqual(report["events"][0]["kind"], "environment")
        self.assertEqual(report["events"][1]["service"], "client")
        self.assertIn("UNSUPPORTED_SCRIPT", codes(report))

    def test_shell_operators_escaping_and_unknown_modifier_stay_unknown(self):
        for command in ("a | b", "a > /output", "a && b", "a *", "[+mystery] a", "waitfor /dev/../x", "display_msg \\}"):
            with self.subTest(command=command):
                report = analyze_text(build(command), contract())
                self.assertGreater(report["summary"]["coverage_gaps"], 0)

    def test_external_scripts_and_truncated_inline_are_coverage_gaps(self):
        external = analyze_text("[+script] .script = host-startup\n", contract())
        self.assertIn("EXTERNAL_SCRIPT", codes(external))
        self.assertIn("UNTERMINATED_INLINE", codes(analyze_text("[+script] .script = {\n display_msg hi", contract())))

    def test_unknown_inherited_modifier_cannot_silently_become_known(self):
        report = analyze_text(build("[+unknown]", "waitfor /dev/a"), contract())
        self.assertEqual(report["events"][-1]["kind"], "unknown")

    def test_input_resource_limits_and_nonfinite_duplicate_contracts(self):
        for source in ("\x00", "x" * 1_048_577, "\n" * 20_001, build(*(["display_msg x"] * 2_001))):
            with self.subTest(length=len(source)):
                with self.assertRaises(ValueError):
                    analyze_text(source, contract())
        for text in ('{"schema":1,"schema":2}', '{"x":NaN}', "[" * 1500 + "]" * 1500):
            with self.assertRaises(ValueError):
                load_contract(text)

    def test_only_lf_and_crlf_can_delimit_script_events(self):
        model = contract(declaration("driver", provides=["/dev/x"]), declaration("client", requires=["/dev/x"]))
        for separator in ("\u2028", "\u2029", "\x85", "\v", "\f", "\r", "\x1c"):
            with self.subTest(separator=repr(separator)):
                with self.assertRaises(ValueError):
                    analyze_text(build("driver &" + separator + "waitfor /dev/x", "client &"), model)
        source = build("driver &", "waitfor /dev/x", "client &")
        lf = analyze_text(source, model)
        crlf = analyze_text(source.replace("\n", "\r\n"), model)
        self.assertEqual(lf["events"], crlf["events"])
        self.assertEqual(lf["summary"], crlf["summary"])

    def test_contract_rejects_unknown_fields_nonliteral_paths_and_invalid_ids(self):
        for change in (lambda x: x.update(extra=True), lambda x: x.update(initial_resources=["/dev/../x"]),
                       lambda x: x["services"][0].update(id="a b"),
                       lambda x: x["services"].append(copy.deepcopy(x["services"][0]))):
            value = contract(declaration("a"))
            change(value)
            with self.assertRaises(ValueError):
                validate_contract(value)


class ArtifactTests(unittest.TestCase):
    def test_comparison_reports_barrier_changes_and_preserves_runtime_caveat(self):
        model = contract(declaration("a", provides=["/dev/a"]), declaration("b", requires=["/dev/a"]))
        before = analyze_text(build("a &", "b &"), model, "before.build")
        after = analyze_text(build("a &", "waitfor /dev/a", "b &"), model, "after.build")
        comparison = compare_reports(before, after)
        self.assertTrue(comparison["event_changes"])
        self.assertIn("RESOURCE_UNGUARDED", {d["code"] for d in comparison["no_longer_reported"]})
        self.assertTrue(any("+waitfor" in line for line in comparison["source_diff"]))
        self.assertFalse(comparison["contract_changed"])
        changed = copy.deepcopy(model)
        changed["initial_resources"] = ["/dev/a"]
        self.assertTrue(compare_reports(before, analyze_text(build("a &", "b &"), changed))["contract_changed"])

    def test_line_only_move_is_separate_from_semantic_change(self):
        a = analyze_text(build("display_msg ready"), contract())
        b = analyze_text("# added comment\n" + build("display_msg ready"), contract())
        delta = compare_reports(a, b)
        self.assertFalse(delta["event_changes"])
        self.assertEqual(delta["line_moves"][0]["after_line"], 3)

    def test_comparison_preserves_duplicate_diagnostic_counts(self):
        model = contract(declaration("a", provides=["/dev/a"]), declaration("b", requires=["/dev/a"]))
        before = analyze_text(build("a &", "b &", "b &"), model)
        after = analyze_text(build("a &", "b &"), model)
        removed = compare_reports(before, after)["no_longer_reported"]
        self.assertEqual(sum(d["code"] == "RESOURCE_UNGUARDED" for d in removed), 1)

    def test_html_escapes_source_and_is_self_contained_without_scripts(self):
        source = build('display_msg "<script>alert(1)</script>"')
        html = render_html(analyze_text(source, contract(), "<unsafe>.build"))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn('src="http', html)
        self.assertIn("id=\"source-L2\"", html)

    def test_cli_generates_reports_and_review_gate_has_distinct_exit_status(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            cmd = [sys.executable, "-m", "boot_order_atlas", "analyze", "examples/serial-before.build", "--contract", "examples/serial-contract.json",
                   "--json", str(output / "report.json"), "--html", str(output / "report.html"), "--fail-on", "warning"]
            run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(json.loads((output / "report.json").read_text())["schema"], "boot-order-atlas.report/v1")
            self.assertTrue((output / "report.html").read_text().startswith("<!doctype html>"))

    def test_cli_never_executes_explicit_shell_or_overwrites_source(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            marker, source = folder / "SHOULD_NOT_EXIST", folder / "input.build"
            source.write_text(build(f"/bin/sh -c 'touch {marker}'"))
            command = [sys.executable, "-m", "boot_order_atlas", "analyze", str(source), "--contract", "examples/empty-contract.json"]
            run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("UNSUPPORTED_SCRIPT", codes(json.loads(run.stdout)))
            self.assertFalse(marker.exists())
            original = source.read_bytes()
            failed = subprocess.run(command + ["--json", str(source)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(source.read_bytes(), original)
            self.assertNotIn("Traceback", failed.stderr)

    def test_cli_missing_invalid_utf8_and_same_outputs_are_clean_input_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "bad.build"
            source.write_bytes(b"\xff")
            base = [sys.executable, "-m", "boot_order_atlas", "analyze", str(source), "--contract", "examples/empty-contract.json"]
            for args in (base, base + ["--json", str(folder / "same"), "--html", str(folder / "same")]):
                result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
