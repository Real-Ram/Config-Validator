"""IPv4 address, subnet mask and subnet-consistency checks (standard library only)."""
import ipaddress

from validators.result import make_bool_result, make_result

CATEGORY = "IP"


def is_valid_ipv4(text):
    """True for a usable-looking IPv4 address: 4 octets 0-255, not 0.0.0.0, not multicast."""
    try:
        address = ipaddress.IPv4Address(text)
    except (ipaddress.AddressValueError, ValueError):
        return False
    if address.is_unspecified or address.is_multicast:
        return False
    return address != ipaddress.IPv4Address("255.255.255.255")


def mask_to_prefix(mask):
    """Return the prefix length (0-32) for '255.255.255.0' or '24', else None.

    A valid dotted mask is a run of 1-bits followed by a run of 0-bits. A wildcard
    such as 0.0.0.255 or a broken mask such as 255.0.255.0 is rejected.
    """
    if mask is None:
        return None
    text = str(mask).lstrip("/")
    if text.isdigit():
        prefix = int(text)
        return prefix if 0 <= prefix <= 32 else None
    try:
        value = int(ipaddress.IPv4Address(text))
    except (ipaddress.AddressValueError, ValueError):
        return None
    inverted = ~value & 0xFFFFFFFF
    if inverted & (inverted + 1) != 0:   # the 0-bits are not one contiguous run at the end
        return None
    return bin(value).count("1")


def host_address_problem(ip, mask):
    """Return a text problem if the address is the network/broadcast address, else None."""
    prefix = mask_to_prefix(mask)
    address = ipaddress.IPv4Address(ip)
    network = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
    if prefix <= 30:   # /31 and /32 have no network/broadcast address
        if address == network.network_address:
            return f"{ip} is the network address of {network}"
        if address == network.broadcast_address:
            return f"{ip} is the broadcast address of {network}"
    return None


def validate_ip_addresses(parsed):
    results = []
    networks = []   # (interface name, IPv4Network) for the overlap check

    for name, interface in parsed["interfaces"].items():
        ip, mask = interface["ip_address"], interface["subnet_mask"]
        if ip is None:
            continue   # interface has no IP configured: nothing to validate here

        actual = f"{ip} {mask if mask else '(no mask)'}"
        problems = []
        if not is_valid_ipv4(ip):
            problems.append(f"'{ip}' is not a valid IPv4 address")
        if mask_to_prefix(mask) is None:
            problems.append(f"'{mask}' is not a valid subnet mask" if mask else "subnet mask is missing")

        results.append(make_bool_result(
            CATEGORY, f"Interface {name} has valid IP address and mask",
            "valid IPv4 address and subnet mask", actual,
            not problems, "; ".join(problems),
        ))
        if problems:
            continue   # the next checks need a valid address and mask

        problem = host_address_problem(ip, mask)
        results.append(make_bool_result(
            CATEGORY, f"Interface {name} IP is a usable host address",
            "host address inside its subnet", actual,
            problem is None, problem or "",
        ))
        networks.append((name, ipaddress.IPv4Network(f"{ip}/{mask_to_prefix(mask)}", strict=False)))

    overlaps = []
    for i, (name_a, net_a) in enumerate(networks):
        for name_b, net_b in networks[i + 1:]:
            if net_a.overlaps(net_b):
                overlaps.append(f"{name_a} ({net_a}) overlaps {name_b} ({net_b})")

    results.append(make_result(
        CATEGORY, "No overlapping subnets between interfaces",
        "no overlaps", "no overlaps" if not overlaps else "; ".join(overlaps),
        "Overlapping subnets: " + "; ".join(overlaps),
    ))
    return results
