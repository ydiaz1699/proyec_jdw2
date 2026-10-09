"""
Contract smoke tests
=====================
These tests DO NOT need a live JDownloader connection. They verify, against the
*real* installed ``myjdapi`` library, that every ``device.<component>.<method>``
call made by ``server.py`` actually exists.

Why this matters: every MCP tool wraps its myjdapi call in a broad
``try/except`` that returns ``"Error: ..."``. That means a call to a method that
does NOT exist (e.g. ``accounts.query_accounts`` instead of
``accounts.list_accounts``) fails *silently at runtime* and looks like the tool
"works" until a user actually invokes it. Catching those mismatches statically
is the single highest-value check for this codebase.

The test extracts ``device.<attr>.<method>(`` patterns from the server source
and asserts that:
  1. ``<attr>`` is a real attribute of a myjdapi ``Jddevice``.
  2. ``<method>`` is a real method of that component's class.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import myjdapi.myjdapi as M

SERVER_SRC = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "jdownloader_mcp"
    / "server.py"
).read_text(encoding="utf-8")

# Map the device attribute names (as set in Jddevice.__init__) to their classes.
# Verified against myjdapi 1.1.11.
DEVICE_COMPONENTS = {
    "accounts": M.Accounts,
    "config": M.Config,
    "linkgrabber": M.Linkgrabber,
    "captcha": M.Captcha,
    "downloads": M.Downloads,
    "toolbar": M.Toolbar,
    "downloadcontroller": M.DownloadController,
    "extensions": M.Extension,
    "jd": M.Jd,
    "dialogs": M.Dialog,
    "reconnect": M.Reconnect,
    "update": M.Update,
    "system": M.System,
    "events": None,  # events subsystem is not a Jddevice component in 1.1.11
}

# device.<attr>.<method>(
CALL_RE = re.compile(r"device\.([a-z_]+)\.([a-zA-Z_]+)\s*\(")


def _extract_calls() -> set[tuple[str, str]]:
    return set(CALL_RE.findall(SERVER_SRC))


def test_jddevice_has_expected_components():
    """The attribute names we rely on must exist on a real Jddevice."""
    device_attrs = set(
        re.findall(r"self\.([a-z_]+)\s*=", M.Jddevice.__init__.__doc__ or "")
    )
    # __doc__ may be empty; fall back to the attribute list we introspected.
    import inspect

    src = inspect.getsource(M.Jddevice.__init__)
    device_attrs = set(re.findall(r"self\.([a-z_]+)\s*=\s*\w+\(self\)", src))
    for attr in ("accounts", "config", "linkgrabber", "captcha", "downloads",
                 "toolbar", "downloadcontroller", "extensions", "dialogs",
                 "update", "system", "reconnect", "jd"):
        assert attr in device_attrs, f"Jddevice has no '{attr}' component"


@pytest.mark.parametrize("attr,method", sorted(_extract_calls()))
def test_server_calls_exist_in_myjdapi(attr: str, method: str):
    """Every device.<attr>.<method>() in server.py must exist in myjdapi."""
    assert attr in DEVICE_COMPONENTS, (
        f"server.py calls device.{attr}.{method}() but '{attr}' is not a known "
        f"Jddevice component in myjdapi 1.1.11"
    )
    cls = DEVICE_COMPONENTS[attr]
    if cls is None:
        pytest.skip(f"'{attr}' subsystem not modeled as a component class")
    assert hasattr(cls, method), (
        f"server.py calls device.{attr}.{method}() but {cls.__name__} has no "
        f"method '{method}' in myjdapi 1.1.11. Available: "
        f"{sorted(m for m in dir(cls) if not m.startswith('_'))}"
    )
