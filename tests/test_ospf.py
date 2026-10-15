from parsers.config_parser import parse_config_text
from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.ospf import validate_ospf


def test_valid_config_passes_ospf_checks(valid, rules):
    assert_all_pass(validate_ospf(valid, rules["ospf"]))


def test_missing_ospf_network_is_detected(load_config, rules):
    results = validate_ospf(load_config("missing_ospf_network"), rules["ospf"])
    assert failed_checks(results) == ["OSPF network 10.0.0.0 0.0.0.3 area 0"]
    assert "192.168.1.0" in get_check(results, "OSPF network 10.0.0.0 0.0.0.3 area 0").reason


def test_missing_ospf_process_is_detected():
    parsed = parse_config_text("hostname R1\n")
    results = validate_ospf(parsed, {"process_id": 1, "router_id": "1.1.1.1"})
    assert failed_checks(results) == ["OSPF process 1 exists"]
    assert len(results) == 1


def test_wrong_process_id_is_detected(valid):
    assert failed_checks(validate_ospf(valid, {"process_id": 2})) == ["OSPF process 2 exists"]


def test_wrong_router_id_is_detected(valid):
    results = validate_ospf(valid, {"process_id": 1, "router_id": "9.9.9.9"})
    result = get_check(results, "OSPF router ID")
    assert (result.expected, result.actual) == ("9.9.9.9", "1.1.1.1")


def test_missing_router_id_is_detected():
    parsed = parse_config_text("router ospf 1\n network 10.0.0.0 0.0.0.3 area 0\n")
    result = get_check(validate_ospf(parsed, {"process_id": 1, "router_id": "1.1.1.1"}), "OSPF router ID")
    assert result.actual == "not configured"


def test_wrong_area_is_detected(valid):
    rule = {"process_id": 1, "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": "1"}]}
    assert failed_checks(validate_ospf(valid, rule)) == ["OSPF network 10.0.0.0 0.0.0.3 area 1"]


def test_dotted_area_in_rules_matches_short_area_in_config(valid):
    rule = {"process_id": 1, "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": "0.0.0.0"}]}
    assert_all_pass(validate_ospf(valid, rule))
