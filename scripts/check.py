"""Meaningful CLI smoke checks in temporary output, without an SDK or network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="atlas-verify-") as temp:
    target = Path(temp)
    subprocess.run([sys.executable, "-m", "boot_order_atlas", "compare", "examples/serial-before.build", "examples/serial-after.build",
                    "--contract", "examples/serial-contract.json", "--json", str(target / "comparison.json"),
                    "--html", str(target / "comparison.html")], cwd=ROOT, check=True)
    report = json.loads((target / "comparison.json").read_text())
    assert report["after"]["summary"]["warning"] == 0
    assert any(d["code"] == "RESOURCE_UNGUARDED" for d in report["no_longer_reported"])
    assert report["after"]["scope"]["target_executed"] is False
    assert "<script" not in (target / "comparison.html").read_text()
print("CLI comparison, artifact escaping, and explicit no-target scope checks passed.")
