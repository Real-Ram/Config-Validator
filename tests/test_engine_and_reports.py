import json

import pytest

from parsers.config_parser import parse_config_file
from reporting.report import build_report, format_terminal_report, write_json_report
from tests.conftest import CONFIG_DIR
from tests.helpers import failed_checks
from validators.engine import run_validations

# config file -> exactly which checks must fail
EXPECTED_FAILURES = {
    "valid_config": [],
    "missing_vlan": ["VLAN 20 exists"],
    "wrong_bgp_neighbor": ["BGP neighbor 10.0.0.2"],
    "missing_ospf_network": ["OSPF network 10.0.0.0 0.0.0.3 area 0"],
    "invalid_interface": [
        "Interface GigabitEthernet1/0/1 IP address",
        "Interface GigabitEthernet1/0/2 IP address",
        "Interface GigabitEthernet1/0/2 admin state",
        "Interface GigabitEthernet1/0/1 has valid IP address and mask",
        "Interface GigabitEthernet1/0/2 has valid IP address and mask",
    ],
}


@pytest.mark.parametrize("config_name", EXPECTED_FAILURES)
def test_engine_finds_exactly_the_expected_failures(config_name, load_config, rules):
    results = run_validations(load_config(config_name), rules)
    assert sorted(failed_checks(results)) == sorted(EXPECTED_FAILURES[config_name])


def test_valid_config_runs_all_check_categories(valid, rules):
    results = run_validations(valid, rules)
    assert {r.category for r in results} == {"Interface", "VLAN", "OSPF", "BGP", "HSRP/VRRP", "IP"}


def test_rules_without_a_section_skip_that_validator(valid):
    results = run_validations(valid, {"vlans": [{"id": 10}]})
    assert {r.category for r in results} == {"VLAN", "IP"}   # IP checks always run


def test_report_summary_counts(load_config, rules):
    results = run_validations(load_config("missing_vlan"), rules)
    report = build_report("configs/missing_vlan.txt", "R1", results, [])
    summary = report["summary"]
    assert summary["failed"] == 1
    assert summary["passed"] + summary["failed"] == summary["total_checks"] == len(results)


def test_report_entry_has_required_fields(load_config, rules):
    results = run_validations(load_config("wrong_bgp_neighbor"), rules)
    report = build_report("x.txt", "R1", results, [])
    entry = next(r for r in report["results"] if r["status"] == "FAIL")
    assert entry["check"] == "BGP neighbor 10.0.0.2"
    assert entry["expected"] == "10.0.0.2 / AS 65002"
    assert entry["actual"] == "10.0.0.2 / AS 65003"
    assert entry["reason"]


def test_passing_entry_has_no_reason(valid, rules):
    report = build_report("x.txt", "R1", run_validations(valid, rules), [])
    assert all(r["reason"] is None for r in report["results"])


def test_json_report_is_written_and_valid(tmp_path, load_config, rules):
    results = run_validations(load_config("missing_vlan"), rules)
    report = build_report("configs/missing_vlan.txt", "R1", results, [])
    path = tmp_path / "out" / "report.json"       # folder does not exist yet
    write_json_report(report, path)
    assert json.loads(path.read_text())["summary"]["failed"] == 1


def test_terminal_report_lists_failures(load_config, rules):
    results = run_validations(load_config("missing_vlan"), rules)
    text = format_terminal_report(build_report("c.txt", "R1", results, []))
    assert "Failed: 1" in text
    assert "FAILED:" in text
    assert "VLAN 20 exists" in text


def test_terminal_report_for_clean_config_has_no_failed_section(valid, rules):
    text = format_terminal_report(build_report("c.txt", "R1", run_validations(valid, rules), []))
    assert "Failed: 0" in text
    assert "FAILED:" not in text


def test_parse_warnings_appear_in_report():
    parsed = parse_config_file(CONFIG_DIR / "valid_config.txt")
    report = build_report("x.txt", "R1", [], ["line 3: something odd"])
    assert report["parse_warnings"] == ["line 3: something odd"]
    assert "line 3: something odd" in format_terminal_report(report)
    assert parsed["warnings"] == []
