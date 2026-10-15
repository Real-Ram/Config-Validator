import json

import pytest

import validate
from validators.rules import RulesError, check_rules_shape, load_rules
from tests.conftest import CONFIG_DIR, RULES_PATH


def test_rules_file_loads():
    assert "bgp" in load_rules(RULES_PATH)


def test_missing_rules_file_raises(tmp_path):
    with pytest.raises(RulesError, match="cannot read"):
        load_rules(tmp_path / "nope.json")


def test_invalid_json_rules_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not json")
    with pytest.raises(RulesError, match="not valid JSON"):
        load_rules(path)


def test_rules_must_be_an_object():
    with pytest.raises(RulesError, match="JSON object"):
        check_rules_shape([1, 2, 3])


def test_rules_section_with_wrong_type_raises():
    with pytest.raises(RulesError, match="must be a list"):
        check_rules_shape({"vlans": {"id": 10}})


def test_rule_missing_required_key_raises():
    with pytest.raises(RulesError, match="missing required key 'id'"):
        check_rules_shape({"vlans": [{"name": "USERS"}]})


def test_bgp_neighbor_missing_remote_as_raises():
    with pytest.raises(RulesError, match="remote_as"):
        check_rules_shape({"bgp": {"local_as": 65001, "neighbors": [{"ip": "10.0.0.2"}]}})


def run_cli(config, tmp_path, rules=RULES_PATH):
    report = tmp_path / "report.json"
    code = validate.main([str(config), "--rules", str(rules), "--report", str(report)])
    return code, report


def test_cli_exit_code_0_for_valid_config(tmp_path, capsys):
    code, report = run_cli(CONFIG_DIR / "valid_config.txt", tmp_path)
    assert code == 0
    assert json.loads(report.read_text())["summary"]["failed"] == 0
    assert "Failed: 0" in capsys.readouterr().out


def test_cli_exit_code_1_when_checks_fail(tmp_path, capsys):
    code, report = run_cli(CONFIG_DIR / "wrong_bgp_neighbor.txt", tmp_path)
    assert code == 1
    assert json.loads(report.read_text())["summary"]["failed"] == 1
    assert "BGP neighbor 10.0.0.2" in capsys.readouterr().out


def test_cli_exit_code_2_for_missing_config(tmp_path, capsys):
    code, report = run_cli(tmp_path / "nope.txt", tmp_path)
    assert code == 2
    assert not report.exists()
    assert "ERROR" in capsys.readouterr().err


def test_cli_exit_code_2_for_malformed_config(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("this is not a config\n")
    code, _ = run_cli(bad, tmp_path)
    assert code == 2


def test_cli_exit_code_2_for_bad_rules(tmp_path):
    bad_rules = tmp_path / "rules.json"
    bad_rules.write_text("{ nope")
    code, _ = run_cli(CONFIG_DIR / "valid_config.txt", tmp_path, rules=bad_rules)
    assert code == 2


def test_cli_default_report_path_uses_config_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = validate.main([str(CONFIG_DIR / "valid_config.txt"), "--rules", str(RULES_PATH)])
    assert code == 0
    assert (tmp_path / "reports" / "valid_config_report.json").exists()
