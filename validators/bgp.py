from validators.result import make_result

CATEGORY = "BGP"


def validate_bgp(parsed, rule):
    """BGP process exists, local AS matches, each expected neighbor has the right remote AS."""
    results = []
    bgp = parsed["bgp"]

    results.append(make_result(
        CATEGORY, "BGP process exists", "present",
        "present" if bgp else "missing", "'router bgp' is not configured",
    ))
    if bgp is None:
        return results

    expected_as = f"AS {rule['local_as']}"
    actual_as = f"AS {bgp['local_as']}"
    results.append(make_result(
        CATEGORY, "BGP local AS", expected_as, actual_as,
        f"Local AS is {bgp['local_as']}, expected {rule['local_as']}",
    ))

    for neighbor in rule.get("neighbors", []):
        ip = neighbor["ip"]
        expected = f"{ip} / AS {neighbor['remote_as']}"
        entry = next((n for n in bgp["neighbors"] if n["ip"] == ip), None)

        if entry is None:
            actual = "not configured"
            reason = f"Neighbor {ip} is not configured"
        else:
            actual = f"{ip} / AS {entry['remote_as']}"
            reason = f"Neighbor {ip} has remote AS {entry['remote_as']}, expected {neighbor['remote_as']}"
        results.append(make_result(CATEGORY, f"BGP neighbor {ip}", expected, actual, reason))
    return results
