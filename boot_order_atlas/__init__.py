"""Host-side review of a bounded subset of QNX SDP 8.0 mkifs scripts."""

__version__ = "0.1.0"

from .analysis import analyze_text, compare_reports
from .contract import load_contract, validate_contract

__all__ = ["analyze_text", "compare_reports", "load_contract", "validate_contract"]
