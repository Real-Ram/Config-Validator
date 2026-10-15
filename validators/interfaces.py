from validators.result import make_result

CATEGORY = "Interface"


def _ip_text(interface):
    if interface["ip_address"] is None:
        return "not configured"
    return f"{interface['ip_address']} {interface['subnet_mask'] or '(no mask)'}"


def _admin_state(interface):
    return {True: "enabled", False: "disabled", None: "not set"}[interface["admin_up"]]


def validate_interfaces(parsed, required):
    """Check every required interface: exists, expected IP/mask, expected admin state."""
    results = []
    for rule in required:
        name = rule["name"]
        interface = parsed["interfaces"].get(name)

        results.append(make_result(
            CATEGORY, f"Interface {name} exists", "present",
            "present" if interface else "missing",
            f"Interface {name} is not configured",
        ))
        if interface is None:
            continue

        if "ip_address" in rule:
            expected = f"{rule['ip_address']} {rule['subnet_mask']}"
            actual = _ip_text(interface)
            results.append(make_result(
                CATEGORY, f"Interface {name} IP address", expected, actual,
                f"Interface {name} has {actual}, expected {expected}",
            ))

        if "enabled" in rule:
            expected = "enabled" if rule["enabled"] else "disabled"
            actual = _admin_state(interface)
            results.append(make_result(
                CATEGORY, f"Interface {name} admin state", expected, actual,
                f"Interface {name} is {actual} (expected {expected}); "
                "'no shutdown' must be present to be enabled",
            ))
    return results
