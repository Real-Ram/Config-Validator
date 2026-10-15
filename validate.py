"""Command line entry point.

Usage:
    python validate.py configs/valid_config.txt
    python validate.py configs/missing_vlan.txt --rules rules/rules.json --report reports/out.json

Exit codes: 0 = all checks passed, 1 = at least one check failed, 2 = could not run
(unreadable/invalid config or rules file). CI systems can use the exit code directly.
"""
import argparse
import sys
from pathlib import Path

from parsers.config_parser import ConfigParseError, parse_config_file
from reporting.report import build_report, format_terminal_report, write_json_report
from validators.engine import run_validations
from validators.rules import RulesError, load_rules


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Validate a Cisco-style config against JSON rules.")
    parser.add_argument("config", help="path to the configuration text file")
    parser.add_argument("--rules", default="rules/rules.json", help="path to the rules JSON file")
    parser.add_argument("--report", help="where to write the JSON report "
                                         "(default: reports/<config name>_report.json)")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    report_path = args.report or f"reports/{Path(args.config).stem}_report.json"

    try:
        rules = load_rules(args.rules)
        parsed = parse_config_file(args.config)
        results = run_validations(parsed, rules)
    except (ConfigParseError, RulesError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = build_report(args.config, parsed["hostname"], results, parsed["warnings"])
    write_json_report(report, report_path)
    print(format_terminal_report(report))
    print(f"\nJSON report written to {report_path}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
