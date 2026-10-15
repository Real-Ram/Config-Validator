from parsers.config_parser import parse_config_text
from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.vlans import validate_vlans


def test_valid_config_passes_vlan_checks(valid, rules):
    assert_all_pass(validate_vlans(valid, rules["vlans"]))


def test_missing_vlan_is_detected(load_config, rules):
    results = validate_vlans(load_config("missing_vlan"), rules["vlans"])
    assert failed_checks(results) == ["VLAN 20 exists"]
    assert get_check(results, "VLAN 20 exists").actual == "missing"


def test_name_check_is_skipped_for_missing_vlan(load_config, rules):
    results = validate_vlans(load_config("missing_vlan"), rules["vlans"])
    assert "VLAN 20 name" not in [r.check for r in results]


def test_wrong_vlan_name_is_detected(valid):
    results = validate_vlans(valid, [{"id": 10, "name": "STAFF"}])
    result = get_check(results, "VLAN 10 name")
    assert not result.passed
    assert (result.expected, result.actual) == ("STAFF", "USERS")


def test_vlan_without_name_is_detected():
    parsed = parse_config_text("vlan 10\n")
    result = get_check(validate_vlans(parsed, [{"id": 10, "name": "USERS"}]), "VLAN 10 name")
    assert result.actual == "no name"
    assert not result.passed


def test_duplicate_vlan_ids_are_detected():
    parsed = parse_config_text("vlan 10\n name A\nvlan 10\n name B\n")
    result = get_check(validate_vlans(parsed, []), "No duplicate VLAN IDs")
    assert not result.passed
    assert "10" in result.actual


def test_out_of_range_vlan_id_is_detected():
    parsed = parse_config_text("vlan 5000\n name TOO_BIG\nvlan 0\n name ZERO\n")
    result = get_check(validate_vlans(parsed, []), "All VLAN IDs are in range 1-4094")
    assert not result.passed
    assert "5000" in result.actual and "0" in result.actual
