from parsers.config_parser import normalize_ospf_area
from validators.result import make_result

CATEGORY = "OSPF"


def validate_ospf(parsed, rule):
    """OSPF process exists, router ID matches, every expected network statement is present."""
    results = []
    process_id = int(rule["process_id"])
    process = parsed["ospf"].get(process_id)

    results.append(make_result(
        CATEGORY, f"OSPF process {process_id} exists", "present",
        "present" if process else "missing",
        f"'router ospf {process_id}' is not configured",
    ))
    if process is None:
        return results

    if "router_id" in rule:
        actual = process["router_id"] or "not configured"
        results.append(make_result(
            CATEGORY, "OSPF router ID", rule["router_id"], actual,
            f"Router ID is {actual}, expected {rule['router_id']}",
        ))

    configured = {(n["network"], n["wildcard"], n["area"]) for n in process["networks"]}
    for network in rule.get("networks", []):
        key = (network["network"], network["wildcard"], normalize_ospf_area(network["area"]))
        text = f"{key[0]} {key[1]} area {key[2]}"
        present = key in configured
        listing = ", ".join(f"{n[0]} {n[1]} area {n[2]}" for n in sorted(configured)) or "none"
        results.append(make_result(
            CATEGORY, f"OSPF network {text}", "configured",
            "configured" if present else "missing",
            f"'network {text}' is not configured (configured networks: {listing})",
        ))
    return results
