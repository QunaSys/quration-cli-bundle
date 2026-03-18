"""Download qret CLI for the current platform and expose it via PATH on import."""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
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


def _release_json(repo: str, tag: str | None) -> dict:
    if tag:
        url = f"{API_BASE}/repos/{repo}/releases/tags/{tag}"
    else:
        url = f"{API_BASE}/repos/{repo}/releases/latest"

    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def _download_file(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=300) as response:
        path.write_bytes(response.read())


def _extract_archive(archive_path: Path, out_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(out_dir)
        return

    if archive_path.name.endswith(".tar.gz"):
        with tarfile.open(archive_path, mode="r:gz") as tf:
            tf.extractall(out_dir)
        return

    raise QretBundleError(f"Unsupported archive format: {archive_path.name}")


def _find_qret_binary(root: Path) -> Path:
    exe_name = "qret.exe" if platform.system() == "Windows" else "qret"
    for path in root.rglob(exe_name):
        if path.is_file():
            if platform.system() != "Windows":
                mode = path.stat().st_mode
                path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return path
    raise QretBundleError(f"Could not find {exe_name} under {root}")


def _append_env_path(var_name: str, entry: str) -> None:
    current = os.environ.get(var_name, "")
    os.environ[var_name] = current + os.pathsep + entry if current else entry


def ensure_qret_on_path() -> Path:
    """Ensure qret is downloaded and available in PATH, returning its full path."""
    repo = os.environ.get("QRET_BUNDLE_REPOSITORY", DEFAULT_REPO)
    tag = os.environ.get("QRET_BUNDLE_TAG")
    asset_name = _platform_asset_name()

    temp_root = Path(tempfile.gettempdir()) / "qret-cli-bundle"
    release_key = tag or "latest"
    install_root = temp_root / repo.replace("/", "__") / release_key / asset_name
    marker = install_root / ".ready"

    if marker.exists():
        qret = _find_qret_binary(install_root)
    else:
        release = _release_json(repo=repo, tag=tag)
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

        qret = _find_qret_binary(install_root)
        marker.write_text("ok", encoding="utf-8")

    bin_dir = qret.parent
    lib_dir = qret.parent.parent / "lib"
    if bin_dir.exists():
        _append_env_path("PATH", str(bin_dir))
    if platform.system() == "Linux" and lib_dir.exists():
        _append_env_path("LD_LIBRARY_PATH", str(lib_dir))
    os.environ["QRET_PATH"] = str(qret)
    return qret


QRET_PATH = ensure_qret_on_path()

__all__ = ["QRET_PATH", "QretBundleError", "ensure_qret_on_path"]
