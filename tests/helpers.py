def failed_checks(results):
    """Names of all checks that failed."""
    return [r.check for r in results if not r.passed]


def get_check(results, check_name):
    """Return the single result with this exact check name."""
    matches = [r for r in results if r.check == check_name]
    assert len(matches) == 1, f"expected exactly one check named {check_name!r}, found {len(matches)}"
    return matches[0]


def assert_all_pass(results):
    bad = [f"{r.check}: expected {r.expected}, actual {r.actual}" for r in results if not r.passed]
    assert not bad, "unexpected failures:\n" + "\n".join(bad)
