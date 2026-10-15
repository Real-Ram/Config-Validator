import pytest

from parsers.config_parser import (ConfigParseError, normalize_ospf_area,
                                   parse_config_file, parse_config_text)


def test_parses_hostname(valid):
    assert valid["hostname"] == "R1"


def test_parses_interface_ip_and_state(valid):
    gi1 = valid["interfaces"]["GigabitEthernet1/0/1"]
    assert gi1["ip_address"] == "192.168.1.1"
    assert gi1["subnet_mask"] == "255.255.255.0"
    assert gi1["admin_up"] is True
    assert gi1["description"] == "LAN"


def test_parses_all_interfaces(valid):
    assert list(valid["interfaces"]) == [
        "Loopback0", "GigabitEthernet1/0/1", "GigabitEthernet1/0/2", "GigabitEthernet1/0/3"]


def test_parses_vlans_in_order(valid):
    assert valid["vlans"] == [
        {"id": 10, "name": "USERS"}, {"id": 20, "name": "SERVERS"}, {"id": 30, "name": "VOICE"}]


def test_parses_ospf_process(valid):
    process = valid["ospf"][1]
    assert process["router_id"] == "1.1.1.1"
    assert {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": "0"} in process["networks"]


def test_parses_bgp_neighbor(valid):
    assert valid["bgp"] == {"local_as": 65001, "neighbors": [{"ip": "10.0.0.2", "remote_as": 65002}]}


def test_parses_hsrp_and_vrrp_groups(valid):
    assert valid["interfaces"]["GigabitEthernet1/0/1"]["hsrp"][1] == {
        "virtual_ip": "192.168.1.254", "priority": 110, "preempt": True}
    assert valid["interfaces"]["GigabitEthernet1/0/3"]["vrrp"][2]["virtual_ip"] == "172.16.0.254"


def test_valid_config_has_no_warnings(valid):
    assert valid["warnings"] == []


def test_comments_and_unknown_commands_are_ignored():
    parsed = parse_config_text("! a comment\nhostname R9\nservice timestamps debug\nip routing\n")
    assert parsed["hostname"] == "R9"
    assert parsed["interfaces"] == {}


def test_shutdown_sets_admin_down():
    parsed = parse_config_text("interface Gi0/1\n shutdown\n")
    assert parsed["interfaces"]["Gi0/1"]["admin_up"] is False


def test_interface_without_shutdown_command_is_not_set():
    parsed = parse_config_text("interface Gi0/1\n ip address 10.0.0.1 255.255.255.0\n")
    assert parsed["interfaces"]["Gi0/1"]["admin_up"] is None


def test_missing_mask_keeps_address_and_records_warning():
    parsed = parse_config_text("interface Gi0/1\n ip address 10.0.0.1\n")
    interface = parsed["interfaces"]["Gi0/1"]
    assert interface["ip_address"] == "10.0.0.1"
    assert interface["subnet_mask"] is None
    assert "line 2" in parsed["warnings"][0]


def test_non_numeric_vlan_id_is_skipped_with_warning():
    parsed = parse_config_text("hostname R1\nvlan abc\n name BAD\n")
    assert parsed["vlans"] == []
    assert "not a number" in parsed["warnings"][0]


def test_malformed_ospf_network_records_warning():
    parsed = parse_config_text("router ospf 1\n network 10.0.0.0 0.0.0.3\n")
    assert parsed["ospf"][1]["networks"] == []
    assert "malformed" in parsed["warnings"][0]


def test_bgp_remote_as_without_number_records_warning():
    parsed = parse_config_text("router bgp 65001\n neighbor 10.0.0.2 remote-as\n")
    assert parsed["bgp"]["neighbors"] == []
    assert "remote-as" in parsed["warnings"][0]


def test_ospf_area_dotted_form_is_normalized():
    parsed = parse_config_text("router ospf 1\n network 10.0.0.0 0.0.0.3 area 0.0.0.0\n")
    assert parsed["ospf"][1]["networks"][0]["area"] == "0"
    assert normalize_ospf_area("0.0.0.1") == "1"


def test_duplicate_vlans_are_both_kept():
    parsed = parse_config_text("vlan 10\n name A\nvlan 10\n name B\n")
    assert [v["name"] for v in parsed["vlans"]] == ["A", "B"]


def test_empty_config_raises():
    with pytest.raises(ConfigParseError, match="empty"):
        parse_config_text("   \n\n")


def test_garbage_text_raises():
    with pytest.raises(ConfigParseError, match="no recognizable"):
        parse_config_text("this is not a router config\nrandom words\n")


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigParseError, match="cannot read"):
        parse_config_file(tmp_path / "nope.txt")
