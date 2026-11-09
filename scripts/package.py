"""Build a deterministic source ZIP; no private/SDK/generated output is included."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / "dist/boot-order-atlas-0.1.0.zip"
output.parent.mkdir(exist_ok=True)
allow = {"boot_order_atlas", "examples", "docs", "tests", "scripts"}
files = [p for p in ROOT.rglob("*") if p.is_file() and not p.is_symlink() and
         ((len(p.relative_to(ROOT).parts) == 1 and p.name in {"README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", ".gitignore"}) or
          p.relative_to(ROOT).parts[0] in allow) and
         "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}]
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        entry = zipfile.ZipInfo("boot-order-atlas/" + path.relative_to(ROOT).as_posix(), (2026, 11, 9, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = (0o100644 << 16)
        archive.writestr(entry, path.read_bytes())
print(f"{output.name}: {len(files)} files, {output.stat().st_size} bytes, sha256={hashlib.sha256(output.read_bytes()).hexdigest()}")
