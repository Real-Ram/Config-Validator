from pathlib import Path

import pytest

from parsers.config_parser import parse_config_file
from validators.rules import load_rules

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "configs"
RULES_PATH = PROJECT_ROOT / "rules" / "rules.json"


@pytest.fixture(scope="session")
def rules():
    return load_rules(RULES_PATH)


@pytest.fixture
def load_config():
    """Returns a function: load_config('valid_config') -> parsed dictionary."""
    def _load(name):
        return parse_config_file(CONFIG_DIR / f"{name}.txt")
    return _load


@pytest.fixture
def valid(load_config):
    return load_config("valid_config")
