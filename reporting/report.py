import json
from datetime import datetime
from pathlib import Path


def build_report(config_file, hostname, results, warnings):
    passed = sum(1 for r in results if r.passed)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_file": str(config_file),
        "hostname": hostname,
        "summary": {
            "total_checks": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "parse_warnings": list(warnings),
        "results": [r.to_dict() for r in results],
    }


def write_json_report(report, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))


def format_terminal_report(report):
    summary = report["summary"]
    lines = [
        f"Config: {report['config_file']} (hostname: {report['hostname'] or 'unknown'})",
        f"Total Checks: {summary['total_checks']}",
        f"Passed: {summary['passed']}",
        f"Failed: {summary['failed']}",
    ]
    failures = [r for r in report["results"] if r["status"] == "FAIL"]
    if failures:
        lines += ["", "FAILED:"]
        for r in failures:
            lines.append(f"- [{r['category']}] {r['check']}")
            lines.append(f"    expected: {r['expected']}")
            lines.append(f"    actual:   {r['actual']}")
            lines.append(f"    reason:   {r['reason']}")
    if report["parse_warnings"]:
        lines += ["", "PARSE WARNINGS:"]
        lines += [f"- {w}" for w in report["parse_warnings"]]
    return "\n".join(lines)
