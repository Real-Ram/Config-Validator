from validators.result import make_result

CATEGORY = "VLAN"


def validate_vlans(parsed, required):
    """Required VLANs exist with the right name; also catches duplicate and out-of-range IDs."""
    results = []
    for rule in required:
        vlan_id = int(rule["id"])
        entry = next((v for v in parsed["vlans"] if v["id"] == vlan_id), None)

        results.append(make_result(
            CATEGORY, f"VLAN {vlan_id} exists", "present",
            "present" if entry else "missing",
            f"VLAN {vlan_id} is not configured",
        ))
        if entry is None:
            continue

        if "name" in rule:
            actual = entry["name"] or "no name"
            results.append(make_result(
                CATEGORY, f"VLAN {vlan_id} name", rule["name"], actual,
                f"VLAN {vlan_id} is named '{actual}', expected '{rule['name']}'",
            ))

    ids = [v["id"] for v in parsed["vlans"]]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    results.append(make_result(
        CATEGORY, "No duplicate VLAN IDs", "no duplicates",
        "no duplicates" if not duplicates else f"duplicate IDs: {duplicates}",
        f"VLAN IDs defined more than once: {duplicates}",
    ))

    out_of_range = sorted({i for i in ids if not 1 <= i <= 4094})
    results.append(make_result(
        CATEGORY, "All VLAN IDs are in range 1-4094", "all in range",
        "all in range" if not out_of_range else f"out of range: {out_of_range}",
        f"VLAN IDs outside 1-4094: {out_of_range}",
    ))
    return results
