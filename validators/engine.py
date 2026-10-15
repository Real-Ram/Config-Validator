from validators.bgp import validate_bgp
from validators.interfaces import validate_interfaces
from validators.ip_checks import validate_ip_addresses
from validators.ospf import validate_ospf
from validators.redundancy import validate_hsrp_vrrp
from validators.vlans import validate_vlans

# Rules section name -> validator function.
# To add a new kind of check: write validate_xxx(parsed, rule) and add one line here.
VALIDATORS = {
    "interfaces": validate_interfaces,
    "vlans": validate_vlans,
    "ospf": validate_ospf,
    "bgp": validate_bgp,
    "redundancy": validate_hsrp_vrrp,
}


def run_validations(parsed, rules):
    """Run every validator that has a section in the rules, plus the IP checks."""
    results = []
    for section, validator in VALIDATORS.items():
        if section in rules:
            results.extend(validator(parsed, rules[section]))
    results.extend(validate_ip_addresses(parsed))   # always runs: basic IP sanity
    return results
