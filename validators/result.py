from dataclasses import dataclass


@dataclass
class CheckResult:
    """One validation outcome: what we expected, what the config has, PASS or FAIL."""

    category: str
    check: str
    expected: str
    actual: str
    passed: bool
    reason: str = ""

    @property
    def status(self):
        return "PASS" if self.passed else "FAIL"

    def to_dict(self):
        return {
            "category": self.category,
            "check": self.check,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
            "reason": self.reason or None,
        }


def make_result(category, check, expected, actual, failure_reason):
    """PASS when expected == actual; the reason is only kept for failures."""
    passed = expected == actual
    return CheckResult(category, check, expected, actual, passed, "" if passed else failure_reason)


def make_bool_result(category, check, expected, actual, passed, failure_reason):
    """Use when PASS/FAIL is decided by logic rather than by comparing two strings."""
    return CheckResult(category, check, expected, actual, passed, "" if passed else failure_reason)
