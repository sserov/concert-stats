"""Run node:test suites for dashboard JS selectors."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("suite", [Path("tests/js")])
def test_js_selectors(suite: Path) -> None:
    result = subprocess.run(
        ["node", "--test", str(suite)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
    assert result.returncode == 0, result.stderr
