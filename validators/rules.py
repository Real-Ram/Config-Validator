"""Load and sanity-check the JSON rules file."""
import json
from pathlib import Path


class RulesError(Exception):
    """Raised when the rules file is missing, not JSON, or has the wrong shape."""


LIST_SECTIONS = {
    "interfaces": ["name"],
    "vlans": ["id"],
    "redundancy": ["protocol", "interface", "group", "virtual_ip"],
}
DICT_SECTIONS = {
    "ospf": ["process_id"],
    "bgp": ["local_as"],
}


def load_rules(path):
    path = Path(path)
    try:
        text = path.read_text()
    except OSError as exc:
        raise RulesError(f"cannot read rules file '{path}': {exc}") from exc
    try:
        rules = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RulesError(f"rules file '{path}' is not valid JSON: {exc}") from exc

    check_rules_shape(rules)
    return rules


def check_rules_shape(rules):
    if not isinstance(rules, dict):
        raise RulesError("rules must be a JSON object")

    for section, required_keys in LIST_SECTIONS.items():
        if section in rules:
            if not isinstance(rules[section], list):
                raise RulesError(f"rules section '{section}' must be a list")
            for entry in rules[section]:
                _require_keys(entry, required_keys, section)

    for section, required_keys in DICT_SECTIONS.items():
        if section in rules:
            if not isinstance(rules[section], dict):
                raise RulesError(f"rules section '{section}' must be an object")
            _require_keys(rules[section], required_keys, section)

    for network in rules.get("ospf", {}).get("networks", []):
        _require_keys(network, ["network", "wildcard", "area"], "ospf.networks")
    for neighbor in rules.get("bgp", {}).get("neighbors", []):
        _require_keys(neighbor, ["ip", "remote_as"], "bgp.neighbors")


def _require_keys(entry, keys, where):
    if not isinstance(entry, dict):
        raise RulesError(f"every entry in '{where}' must be an object")
    for key in keys:
        if key not in entry:
            raise RulesError(f"rule in '{where}' is missing required key '{key}'")
