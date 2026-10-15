from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.interfaces import validate_interfaces


def test_valid_config_passes_interface_checks(valid, rules):
    assert_all_pass(validate_interfaces(valid, rules["interfaces"]))


def test_missing_interface_is_detected(valid):
    rule = [{"name": "GigabitEthernet9/9/9", "ip_address": "10.9.9.1", "subnet_mask": "255.255.255.0"}]
    results = validate_interfaces(valid, rule)
    assert failed_checks(results) == ["Interface GigabitEthernet9/9/9 exists"]
    assert len(results) == 1   # IP/state checks are skipped when the interface is missing


def test_wrong_ip_address_is_detected(valid):
    rule = [{"name": "GigabitEthernet1/0/1", "ip_address": "192.168.1.2", "subnet_mask": "255.255.255.0"}]
    result = get_check(validate_interfaces(valid, rule), "Interface GigabitEthernet1/0/1 IP address")
    assert not result.passed
    assert result.expected == "192.168.1.2 255.255.255.0"
    assert result.actual == "192.168.1.1 255.255.255.0"


def test_wrong_mask_is_detected(valid):
    rule = [{"name": "GigabitEthernet1/0/1", "ip_address": "192.168.1.1", "subnet_mask": "255.255.0.0"}]
    assert failed_checks(validate_interfaces(valid, rule)) == ["Interface GigabitEthernet1/0/1 IP address"]


def test_shutdown_interface_is_detected(load_config, rules):
    results = validate_interfaces(load_config("invalid_interface"), rules["interfaces"])
    state = get_check(results, "Interface GigabitEthernet1/0/2 admin state")
    assert not state.passed
    assert state.actual == "disabled"


def test_interface_without_no_shutdown_is_not_enabled(valid):
    rule = [{"name": "Loopback0", "enabled": True}]   # Loopback0 has no 'no shutdown' line
    result = get_check(validate_interfaces(valid, rule), "Interface Loopback0 admin state")
    assert not result.passed
    assert result.actual == "not set"


def test_invalid_interface_config_fails_ip_checks(load_config, rules):
    results = validate_interfaces(load_config("invalid_interface"), rules["interfaces"])
    assert failed_checks(results) == [
        "Interface GigabitEthernet1/0/1 IP address",
        "Interface GigabitEthernet1/0/2 IP address",
        "Interface GigabitEthernet1/0/2 admin state",
    ]
