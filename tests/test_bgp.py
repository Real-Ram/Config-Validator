from parsers.config_parser import parse_config_text
from tests.helpers import assert_all_pass, failed_checks, get_check
from validators.bgp import validate_bgp


def test_valid_config_passes_bgp_checks(valid, rules):
    assert_all_pass(validate_bgp(valid, rules["bgp"]))


def test_wrong_remote_as_is_detected(load_config, rules):
    results = validate_bgp(load_config("wrong_bgp_neighbor"), rules["bgp"])
    assert failed_checks(results) == ["BGP neighbor 10.0.0.2"]
    result = get_check(results, "BGP neighbor 10.0.0.2")
    assert result.expected == "10.0.0.2 / AS 65002"
    assert result.actual == "10.0.0.2 / AS 65003"


def test_missing_neighbor_is_detected(valid):
    rule = {"local_as": 65001, "neighbors": [{"ip": "10.0.0.99", "remote_as": 65009}]}
    result = get_check(validate_bgp(valid, rule), "BGP neighbor 10.0.0.99")
    assert not result.passed
    assert result.actual == "not configured"


def test_wrong_local_as_is_detected(valid):
    results = validate_bgp(valid, {"local_as": 65100})
    assert failed_checks(results) == ["BGP local AS"]


def test_missing_bgp_process_is_detected():
    parsed = parse_config_text("hostname R1\n")
    results = validate_bgp(parsed, {"local_as": 65001, "neighbors": [{"ip": "10.0.0.2", "remote_as": 65002}]})
    assert failed_checks(results) == ["BGP process exists"]
    assert len(results) == 1
