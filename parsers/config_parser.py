"""Turn Cisco-style configuration text into plain Python dictionaries and lists.

The parser only READS the text. It does not decide whether the configuration is
correct; the validators do that. If a line it understands is malformed (for example
'ip address 10.0.0.1' without a mask) it keeps what it found and records a warning.
"""
import ipaddress
from pathlib import Path


class ConfigParseError(Exception):
    """Raised when the configuration cannot be read or has nothing recognizable."""


def parse_config_file(path):
    path = Path(path)
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigParseError(f"cannot read configuration file '{path}': {exc}") from exc
    return parse_config_text(text)


def parse_config_text(text):
    """Parse configuration text into a dictionary.

    Result shape:
    {
      "hostname": "R1",
      "interfaces": {"Gi1/0/1": {"description", "ip_address", "subnet_mask",
                                 "admin_up", "hsrp": {group: {...}}, "vrrp": {group: {...}}}},
      "vlans": [{"id": 10, "name": "USERS"}, ...],          # a list, so duplicates are visible
      "ospf": {1: {"router_id": "1.1.1.1", "networks": [{"network", "wildcard", "area"}]}},
      "bgp": {"local_as": 65001, "neighbors": [{"ip": "10.0.0.2", "remote_as": 65002}]} or None,
      "warnings": ["line 12: ..."],
    }
    """
    if not text.strip():
        raise ConfigParseError("configuration is empty")

    parsed = {
        "hostname": None,
        "interfaces": {},
        "vlans": [],
        "ospf": {},
        "bgp": None,
        "warnings": [],
    }

    # "current" is the block the indented lines belong to: (kind, dictionary)
    current = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            continue

        tokens = stripped.split()

        if not raw_line[0].isspace():
            current = _start_block(parsed, tokens, lineno)
        elif current is not None:
            _parse_block_line(current, tokens, lineno, parsed["warnings"])

    if not (parsed["hostname"] or parsed["interfaces"] or parsed["vlans"]
            or parsed["ospf"] or parsed["bgp"]):
        raise ConfigParseError(
            "no recognizable configuration found "
            "(expected hostname, interface, vlan, router ospf or router bgp)"
        )
    return parsed


def normalize_ospf_area(area):
    """'0.0.0.0' and '0' mean the same OSPF area; store the short form."""
    area = str(area)
    if "." in area:
        try:
            return str(int(ipaddress.IPv4Address(area)))
        except ipaddress.AddressValueError:
            return area
    return area


# ---------------------------------------------------------------------------
# Block headers: lines that start in column 0
# ---------------------------------------------------------------------------

def _start_block(parsed, tokens, lineno):
    keyword = tokens[0]

    if keyword == "hostname" and len(tokens) >= 2:
        parsed["hostname"] = tokens[1]
        return None

    if keyword == "interface" and len(tokens) >= 2:
        name = " ".join(tokens[1:])
        interface = parsed["interfaces"].setdefault(name, {
            "description": None,
            "ip_address": None,
            "subnet_mask": None,
            "admin_up": None,   # True = 'no shutdown', False = 'shutdown', None = not stated
            "hsrp": {},
            "vrrp": {},
        })
        return ("interface", interface)

    if keyword == "vlan" and len(tokens) == 2:
        if not tokens[1].isdigit():
            parsed["warnings"].append(f"line {lineno}: VLAN id '{tokens[1]}' is not a number")
            return None
        vlan = {"id": int(tokens[1]), "name": None}
        parsed["vlans"].append(vlan)
        return ("vlan", vlan)

    if tokens[:2] == ["router", "ospf"] and len(tokens) >= 3:
        if not tokens[2].isdigit():
            parsed["warnings"].append(f"line {lineno}: OSPF process id '{tokens[2]}' is not a number")
            return None
        process = parsed["ospf"].setdefault(int(tokens[2]), {"router_id": None, "networks": []})
        return ("ospf", process)

    if tokens[:2] == ["router", "bgp"] and len(tokens) >= 3:
        if not tokens[2].isdigit():
            parsed["warnings"].append(f"line {lineno}: BGP AS '{tokens[2]}' is not a number")
            return None
        if parsed["bgp"] is None:
            parsed["bgp"] = {"local_as": int(tokens[2]), "neighbors": []}
        return ("bgp", parsed["bgp"])

    return None  # any other top-level command is ignored


# ---------------------------------------------------------------------------
# Lines inside a block: lines that start with a space
# ---------------------------------------------------------------------------

def _parse_block_line(current, tokens, lineno, warnings):
    kind, block = current
    if kind == "interface":
        _parse_interface_line(block, tokens, lineno, warnings)
    elif kind == "vlan":
        if tokens[0] == "name" and len(tokens) >= 2:
            block["name"] = " ".join(tokens[1:])
    elif kind == "ospf":
        _parse_ospf_line(block, tokens, lineno, warnings)
    elif kind == "bgp":
        _parse_bgp_line(block, tokens, lineno, warnings)


def _parse_interface_line(interface, tokens, lineno, warnings):
    if tokens[0] == "description":
        interface["description"] = " ".join(tokens[1:])

    elif tokens[:2] == ["ip", "address"]:
        if "secondary" in tokens:
            return  # secondary addresses are not validated in this project
        if len(tokens) >= 4:
            interface["ip_address"], interface["subnet_mask"] = tokens[2], tokens[3]
        elif len(tokens) == 3:
            interface["ip_address"] = tokens[2]
            warnings.append(f"line {lineno}: 'ip address' has no subnet mask")
        else:
            warnings.append(f"line {lineno}: 'ip address' has no address")

    elif tokens == ["shutdown"]:
        interface["admin_up"] = False
    elif tokens == ["no", "shutdown"]:
        interface["admin_up"] = True

    elif tokens[0] == "standby":
        _parse_redundancy_line(interface["hsrp"], tokens, lineno, warnings)
    elif tokens[0] == "vrrp":
        _parse_redundancy_line(interface["vrrp"], tokens, lineno, warnings)


def _parse_redundancy_line(groups, tokens, lineno, warnings):
    """Handles both 'standby 1 ip 10.0.0.254' (HSRP) and 'vrrp 1 ip 10.0.0.254' (VRRP)."""
    if len(tokens) < 3 or not tokens[1].isdigit():
        return  # e.g. 'standby version 2' - not a group command
    group = groups.setdefault(int(tokens[1]), {"virtual_ip": None, "priority": None, "preempt": False})
    subcommand = tokens[2]

    if subcommand == "ip":
        if len(tokens) >= 4:
            group["virtual_ip"] = tokens[3]
        else:
            warnings.append(f"line {lineno}: '{tokens[0]} {tokens[1]} ip' has no address")
    elif subcommand == "priority" and len(tokens) >= 4 and tokens[3].isdigit():
        group["priority"] = int(tokens[3])
    elif subcommand == "preempt":
        group["preempt"] = True


def _parse_ospf_line(process, tokens, lineno, warnings):
    if tokens[0] == "router-id" and len(tokens) >= 2:
        process["router_id"] = tokens[1]
    elif tokens[0] == "network":
        # network 192.168.1.0 0.0.0.255 area 0
        if len(tokens) == 5 and tokens[3] == "area":
            process["networks"].append({
                "network": tokens[1],
                "wildcard": tokens[2],
                "area": normalize_ospf_area(tokens[4]),
            })
        else:
            warnings.append(f"line {lineno}: malformed OSPF 'network' statement")


def _parse_bgp_line(bgp, tokens, lineno, warnings):
    # neighbor 10.0.0.2 remote-as 65002
    if tokens[0] == "neighbor" and len(tokens) >= 2 and "remote-as" in tokens:
        index = tokens.index("remote-as")
        if index + 1 < len(tokens) and tokens[index + 1].isdigit():
            bgp["neighbors"].append({"ip": tokens[1], "remote_as": int(tokens[index + 1])})
        else:
            warnings.append(f"line {lineno}: BGP 'remote-as' has no valid AS number")
