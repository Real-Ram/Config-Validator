# Network Configuration Validator

A small Python tool that reads a Cisco-style configuration file, turns it into
structured data, and checks it against configurable JSON rules. It reports
PASS/FAIL for each check and writes a JSON report.

It runs locally on text files. No router, no SSH, no third-party parsing library.

## Problem statement

Configuration mistakes cause outages: a VLAN missing on a switch, a wrong BGP
remote AS, an OSPF network that was never added, an IP address with a typo.
Checking this by reading configs by hand does not scale and is easy to get wrong.
This tool states the expected configuration once (in `rules/rules.json`) and checks
any config against it automatically.

## How it works

```
Cisco-style config text
        |
        v
   parsers/config_parser.py     text -> dictionaries and lists
        |
        v
   validators/engine.py         runs each validator that has a section in the rules
        |
        v
   PASS / FAIL results          (check, expected, actual, status, reason)
        |
        v
   reporting/report.py          terminal summary + JSON report
```

## Features

- Parser for hostname, interfaces (IP, mask, shutdown state, description), VLANs, OSPF, BGP, HSRP and VRRP
- Interface checks: exists, expected IP and mask, enabled (`no shutdown`)
- VLAN checks: exists, correct name, no duplicate IDs, IDs in range 1-4094
- OSPF checks: process exists, router ID, expected `network` statements (area `0` and `0.0.0.0` are treated as equal)
- BGP checks: process exists, local AS, expected neighbor with expected remote AS
- HSRP/VRRP checks: expected group and virtual IP on an interface
- IP checks (Python `ipaddress` module): valid IPv4 address, valid subnet mask, address is not the network or broadcast address, no overlapping subnets
- Warnings for malformed lines instead of crashing (for example `ip address 10.0.0.1` with no mask)
- Clear errors for empty or unrecognizable configs and invalid rules files
- Exit codes: 0 all passed, 1 some checks failed, 2 could not run (usable from CI)
- Five sample configs: valid, missing VLAN, wrong BGP neighbor, missing OSPF network, invalid interface

## Technologies

Python 3 and pytest. Everything else is the standard library (`ipaddress`, `json`, `argparse`, `dataclasses`, `pathlib`).

## Project structure

```
.
├── parsers/config_parser.py     config text -> structured data
├── validators/
│   ├── engine.py                maps rule sections to validator functions
│   ├── interfaces.py  vlans.py  ospf.py  bgp.py  redundancy.py  ip_checks.py
│   ├── result.py                CheckResult (one PASS/FAIL outcome)
│   └── rules.py                 loads and sanity-checks the rules JSON
├── reporting/report.py          JSON report and terminal report
├── rules/rules.json             expected configuration
├── configs/                     sample configurations
├── tests/                       pytest tests
├── reports/                     generated reports (not committed)
└── validate.py                  command line entry point
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python validate.py configs/valid_config.txt
python validate.py configs/wrong_bgp_neighbor.txt
python validate.py configs/valid_config.txt --rules rules/rules.json --report reports/my_report.json
```

By default the JSON report goes to `reports/<config name>_report.json`.

## Run the tests

```bash
pytest
```

## Example output

Valid configuration:

```
Config: configs/valid_config.txt (hostname: R1)
Total Checks: 37
Passed: 37
Failed: 0
```

BGP neighbor with the wrong remote AS (`configs/wrong_bgp_neighbor.txt`):

```
Config: configs/wrong_bgp_neighbor.txt (hostname: R1)
Total Checks: 37
Passed: 36
Failed: 1

FAILED:
- [BGP] BGP neighbor 10.0.0.2
    expected: 10.0.0.2 / AS 65002
    actual:   10.0.0.2 / AS 65003
    reason:   Neighbor 10.0.0.2 has remote AS 65003, expected 65002
```

Matching entry in the JSON report:

```json
{
  "category": "BGP",
  "check": "BGP neighbor 10.0.0.2",
  "expected": "10.0.0.2 / AS 65002",
  "actual": "10.0.0.2 / AS 65003",
  "status": "FAIL",
  "reason": "Neighbor 10.0.0.2 has remote AS 65003, expected 65002"
}
```

Invalid interface configuration (`configs/invalid_interface.txt`) is caught by two layers:
the interface rules (wrong address, interface shut down) and the IP checks
(`192.168.1.300` is not a valid address, `255.255.255.25` is not a valid mask).

## Rules file

`rules/rules.json` has one optional section per validator: `interfaces`, `vlans`,
`ospf`, `bgp`, `redundancy`. A section that is missing is skipped. IP sanity checks
always run. Example:

```json
{
  "bgp": {"local_as": 65001, "neighbors": [{"ip": "10.0.0.2", "remote_as": 65002}]}
}
```

## Adding a new check

1. Write `validate_something(parsed, rule)` in `validators/` returning a list of `CheckResult`.
2. Add one line to `VALIDATORS` in `validators/engine.py`.
3. Add a section to `rules.json` and tests.

## Limitations

- Supports the commands listed above; other lines are ignored.
- Interface names must match exactly (`Gi1/0/1` is not treated as `GigabitEthernet1/0/1`).
- IPv4 only; secondary addresses are ignored.
- One config file per run; no real devices, no SSH.
- Cisco IOS-style syntax only.

## Future improvements

- Validate many configs in one run (a directory of files, one rule set per device)
- Interface name normalization
- IPv6 and EIGRP checks
- A parser for another vendor behind the same output structure
- GitHub Actions workflow running `pytest` and `validate.py`
