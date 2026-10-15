import pytest

from parsers.config_parser import parse_config_text
from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.ip_checks import (host_address_problem, is_valid_ipv4, mask_to_prefix,
                                  validate_ip_addresses)


@pytest.mark.parametrize("address", ["192.168.1.1", "10.0.0.1", "1.1.1.1", "172.16.0.254"])
def test_valid_ipv4_addresses(address):
    assert is_valid_ipv4(address)


@pytest.mark.parametrize("address", [
    "192.168.1.300", "192.168.1", "192.168.1.1.1", "abc.def.ghi.jkl",
    "", "0.0.0.0", "224.0.0.1", "255.255.255.255", "192.168.01.1",
])
def test_invalid_ipv4_addresses(address):
    assert not is_valid_ipv4(address)


@pytest.mark.parametrize("mask, prefix", [
    ("255.255.255.0", 24), ("255.255.255.252", 30), ("255.255.255.255", 32),
    ("255.0.0.0", 8), ("0.0.0.0", 0), ("24", 24), ("/30", 30),
])
def test_valid_masks_and_prefixes(mask, prefix):
    assert mask_to_prefix(mask) == prefix


@pytest.mark.parametrize("mask", [
    "255.255.255.25", "255.0.255.0", "0.0.0.255", "255.255.255", "33", "abc", "", None,
])
def test_invalid_masks(mask):
    assert mask_to_prefix(mask) is None


def test_network_address_is_not_a_usable_host():
    assert "network address" in host_address_problem("192.168.1.0", "255.255.255.0")


def test_broadcast_address_is_not_a_usable_host():
    assert "broadcast address" in host_address_problem("192.168.1.255", "255.255.255.0")


@pytest.mark.parametrize("ip, mask", [
    ("192.168.1.1", "255.255.255.0"),
    ("10.0.0.0", "255.255.255.254"),    # /31 point-to-point: both addresses usable
    ("1.1.1.1", "255.255.255.255"),     # /32 loopback
])
def test_usable_host_addresses(ip, mask):
    assert host_address_problem(ip, mask) is None


def test_valid_config_passes_all_ip_checks(valid):
    assert_all_pass(validate_ip_addresses(valid))


def test_invalid_ip_and_mask_are_reported(load_config):
    results = validate_ip_addresses(load_config("invalid_interface"))
    assert failed_checks(results) == [
        "Interface GigabitEthernet1/0/1 has valid IP address and mask",
        "Interface GigabitEthernet1/0/2 has valid IP address and mask",
    ]
    assert "192.168.1.300" in get_check(
        results, "Interface GigabitEthernet1/0/1 has valid IP address and mask").reason


def test_missing_mask_is_reported():
    parsed = parse_config_text("interface Gi0/1\n ip address 10.0.0.1\n")
    result = get_check(validate_ip_addresses(parsed), "Interface Gi0/1 has valid IP address and mask")
    assert not result.passed
    assert "mask is missing" in result.reason


def test_network_address_on_interface_is_reported():
    parsed = parse_config_text("interface Gi0/1\n ip address 192.168.1.0 255.255.255.0\n")
    result = get_check(validate_ip_addresses(parsed), "Interface Gi0/1 IP is a usable host address")
    assert not result.passed


def test_overlapping_subnets_are_reported():
    parsed = parse_config_text(
        "interface Gi0/1\n ip address 192.168.1.1 255.255.255.0\n"
        "interface Gi0/2\n ip address 192.168.1.129 255.255.255.128\n")
    result = get_check(validate_ip_addresses(parsed), "No overlapping subnets between interfaces")
    assert not result.passed
    assert "Gi0/1" in result.actual and "Gi0/2" in result.actual


def test_interface_without_ip_is_ignored():
    parsed = parse_config_text("interface Gi0/1\n no shutdown\n")
    results = validate_ip_addresses(parsed)
    assert [r.check for r in results] == ["No overlapping subnets between interfaces"]
