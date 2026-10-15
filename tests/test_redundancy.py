import pytest

from parsers.config_parser import parse_config_text
from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.redundancy import validate_hsrp_vrrp
from validators.rules import RulesError


def test_valid_config_passes_hsrp_and_vrrp_checks(valid, rules):
    assert_all_pass(validate_hsrp_vrrp(valid, rules["redundancy"]))


def test_wrong_virtual_ip_is_detected(valid):
    rule = [{"protocol": "hsrp", "interface": "GigabitEthernet1/0/1", "group": 1, "virtual_ip": "192.168.1.253"}]
    result = get_check(validate_hsrp_vrrp(valid, rule), "HSRP group 1 on GigabitEthernet1/0/1")
    assert not result.passed
    assert (result.expected, result.actual) == ("virtual IP 192.168.1.253", "virtual IP 192.168.1.254")


def test_missing_hsrp_group_is_detected(valid):
    rule = [{"protocol": "hsrp", "interface": "GigabitEthernet1/0/2", "group": 1, "virtual_ip": "10.0.0.254"}]
    result = get_check(validate_hsrp_vrrp(valid, rule), "HSRP group 1 on GigabitEthernet1/0/2")
    assert result.actual == "not configured"


def test_missing_vrrp_group_is_detected(valid):
    rule = [{"protocol": "vrrp", "interface": "GigabitEthernet1/0/1", "group": 1, "virtual_ip": "192.168.1.254"}]
    assert failed_checks(validate_hsrp_vrrp(valid, rule)) == ["VRRP group 1 on GigabitEthernet1/0/1"]


def test_unknown_interface_is_detected(valid):
    rule = [{"protocol": "hsrp", "interface": "Vlan99", "group": 1, "virtual_ip": "10.9.9.254"}]
    result = get_check(validate_hsrp_vrrp(valid, rule), "HSRP group 1 on Vlan99")
    assert result.actual == "interface not found"


def test_group_without_virtual_ip_is_detected():
    parsed = parse_config_text("interface Gi0/1\n standby 1 priority 100\n")
    rule = [{"protocol": "hsrp", "interface": "Gi0/1", "group": 1, "virtual_ip": "10.0.0.254"}]
    result = get_check(validate_hsrp_vrrp(parsed, rule), "HSRP group 1 on Gi0/1")
    assert result.actual == "no virtual IP"


def test_unknown_protocol_in_rules_raises(valid):
    rule = [{"protocol": "glbp", "interface": "Gi0/1", "group": 1, "virtual_ip": "10.0.0.254"}]
    with pytest.raises(RulesError, match="glbp"):
        validate_hsrp_vrrp(valid, rule)
