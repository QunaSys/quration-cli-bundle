"""Download qret CLI for the current platform and expose it via PATH on import."""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

API_BASE = "https://api.github.com"
DEFAULT_REPO = "QunaSys/quration-cli-bundle"


class QretBundleError(RuntimeError):
    """Raised when qret bundle resolution or download fails."""


def _platform_asset_name() -> str:
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Darwin":
        if machine in {"x86_64", "amd64"}:
            return "qret-macos-15-intel.tar.gz"
        return "qret-macos-latest.tar.gz"
    if system == "Linux":
        return "qret-ubuntu-latest.tar.gz"
    if system == "Windows":
        return "qret-windows-latest.zip"

    raise QretBundleError(f"Unsupported platform: {system} ({machine})")


def _release_json() -> dict:
    url = f"{API_BASE}/repos/{DEFAULT_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def _download_file(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=300) as response:
        path.write_bytes(response.read())


def _extract_archive(archive_path: Path, out_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="qret-extract-") as tmp_dir:
        extract_tmp = Path(tmp_dir)

        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_tmp)
        elif archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, mode="r:gz") as tf:
                tf.extractall(extract_tmp)
        else:
            raise QretBundleError(f"Unsupported archive format: {archive_path.name}")

        payload_root = extract_tmp
        while True:
            entries = [p for p in payload_root.iterdir()]
            dirs = [p for p in entries if p.is_dir()]
            files = [p for p in entries if p.is_file()]
            # Collapse redundant wrapper directories (e.g., qret-*/qret-*/...).
            if len(dirs) == 1 and len(files) == 0:
                payload_root = dirs[0]
                continue
            break

        for path in payload_root.iterdir():
            target = out_dir / path.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(path), str(target))


def _append_env_path(var_name: str, entry: str) -> None:
    current = os.environ.get(var_name, "")
    os.environ[var_name] = current + os.pathsep + entry if current else entry


def ensure_qret_on_path() -> None:

    install_root = Path(__file__).parent / "bundle"
    bin_dir = install_root / "bin"
    lib_dir = install_root / "lib"
    _append_env_path("PATH", str(bin_dir))
    if platform.system() == "Linux":
        _append_env_path("LD_LIBRARY_PATH", str(lib_dir))
    
    if not (bin_dir / "qret").exists() or not (bin_dir / "gridsynth").exists():
        asset_name = _platform_asset_name()
        release = _release_json()
        assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
        if asset_name not in assets:
            available = ", ".join(sorted(assets.keys()))
            raise QretBundleError(
                f"Asset {asset_name!r} not found in release. Available assets: {available}"
            )

        if install_root.exists():
            shutil.rmtree(install_root)
        install_root.mkdir(parents=True, exist_ok=True)

        archive_path = install_root / asset_name
        _download_file(assets[asset_name], archive_path)
        _extract_archive(archive_path, install_root)
        archive_path.unlink(missing_ok=True)

    if (bin_dir / "gridsynth").exists():
        os.environ["GRIDSYNTH_PATH"] = str(bin_dir / "gridsynth")


ensure_qret_on_path()


def _run_streamlit(script_name: str, *streamlit_args: str) -> subprocess.CompletedProcess[bytes]:
    streamlit_cmd = shutil.which("streamlit")
    if streamlit_cmd is None:
        msg = "streamlit command was not found in PATH. Please install streamlit."
        raise QretBundleError(msg)

    script_path = Path(__file__).resolve().parent / "visualizer" / script_name
    if not script_path.is_file():
        msg = f"Bundled visualizer script not found: {script_path}"
        raise QretBundleError(msg)

    cmd = [streamlit_cmd, "run", str(script_path), *streamlit_args]
    return subprocess.run(cmd, check=False)


def visualize_compile_info(*streamlit_args: str) -> subprocess.CompletedProcess[bytes]:
    """Run streamlit visualizer for compile information."""
    return _run_streamlit("visualize_compile_info.py", *streamlit_args)


def visualize_computational_process(*streamlit_args: str) -> subprocess.CompletedProcess[bytes]:
    """Run streamlit visualizer for computational process."""
    return _run_streamlit("visualize_computational_process.py", *streamlit_args)


__all__ = [
    "QretBundleError",
    "ensure_qret_on_path",
    "visualize_compile_info",
    "visualize_computational_process",
]
