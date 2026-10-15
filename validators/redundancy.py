from validators.result import make_result
from validators.rules import RulesError

CATEGORY = "HSRP/VRRP"
SUPPORTED = ("hsrp", "vrrp")


def validate_hsrp_vrrp(parsed, required):
    """Each required interface has the expected HSRP or VRRP group and virtual IP."""
    results = []
    for rule in required:
        protocol = str(rule["protocol"]).lower()
        if protocol not in SUPPORTED:
            raise RulesError(f"unknown redundancy protocol '{rule['protocol']}' (use hsrp or vrrp)")

        name, group = rule["interface"], int(rule["group"])
        check = f"{protocol.upper()} group {group} on {name}"
        expected = f"virtual IP {rule['virtual_ip']}"
        interface = parsed["interfaces"].get(name)

        if interface is None:
            actual, reason = "interface not found", f"Interface {name} is not configured"
        elif group not in interface[protocol]:
            actual, reason = "not configured", f"{protocol.upper()} group {group} is not configured on {name}"
        else:
            virtual_ip = interface[protocol][group]["virtual_ip"]
            actual = f"virtual IP {virtual_ip}" if virtual_ip else "no virtual IP"
            reason = f"{protocol.upper()} group {group} on {name} has {actual}, expected {expected}"

        results.append(make_result(CATEGORY, check, expected, actual, reason))
    return results
