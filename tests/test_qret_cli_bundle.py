from __future__ import annotations

import importlib.util
import os
import subprocess
import shutil
from pathlib import Path


def test_import_and_qret_version() -> None:
    import qret_cli_bundle  # noqa: F401

    qret_executable = shutil.which("qret") or shutil.which("qret.exe") or shutil.which("qret.cmd")
    assert qret_executable is not None

    result = subprocess.run(
        [qret_executable, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() or result.stderr.strip()

    gridsynth_path = os.environ.get("GRIDSYNTH_PATH")
    assert gridsynth_path is not None
