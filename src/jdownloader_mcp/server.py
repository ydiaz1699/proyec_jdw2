#!/usr/bin/env python3
"""
JDownloader MCP Server
======================
Model Context Protocol server that exposes the full JDownloader API
via myjdapi as tools that any LLM can invoke.

Requires: pip install myjdapi mcp
"""

import os
import json
import logging
from typing import Any, Optional
from contextlib import asynccontextmanager

import myjdapi
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jdownloader-mcp")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_jd: Optional[myjdapi.Myjdapi] = None
_device = None



# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "jdownloader",
    description="Full JDownloader API via My.JDownloader remote control",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _get_env(key: str, required: bool = True) -> Optional[str]:
    """Get environment variable."""
    val = os.environ.get(key)
    if required and not val:
        raise ValueError(f"Environment variable {key} is not set")
    return val


def _ensure_connected():
    """Ensure we have an active connection and device."""
    global _jd, _device
    if _jd is None or _device is None:
        raise RuntimeError(
            "Not connected to JDownloader. Call jd_connect first."
        )
    return _device


def _format_size(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    if bytes_val is None or bytes_val == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_val) < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"



# ===========================================================================
# CONNECTION TOOLS
# ===========================================================================

@mcp.tool()
def jd_connect(
    email: Optional[str] = None,
    password: Optional[str] = None,
    device_name: Optional[str] = None,
    app_key: str = "mcp-jdownloader-server"
) -> str:
    """
    Connect to My.JDownloader and select a device.

    Credentials can be passed as parameters or set via environment variables:
    - JD_EMAIL
    - JD_PASSWORD
    - JD_DEVICE_NAME (optional, uses first device if not set)

    Args:
        email: My.JDownloader account email (or use JD_EMAIL env var)
        password: My.JDownloader account password (or use JD_PASSWORD env var)
        device_name: Name of the JDownloader device to control (optional)
        app_key: Application key for the API session
    """
    global _jd, _device

    email = email or os.environ.get("JD_EMAIL")
    password = password or os.environ.get("JD_PASSWORD")
    device_name = device_name or os.environ.get("JD_DEVICE_NAME")

    if not email or not password:
        return "Error: email and password are required (pass them or set JD_EMAIL/JD_PASSWORD env vars)"

    try:
        _jd = myjdapi.Myjdapi()
        _jd.set_app_key(app_key)
        _jd.connect(email, password)
        _jd.update_devices()
        devices = _jd.list_devices()

        if not devices:
            return "Error: No devices linked to this account"

        if device_name:
            _device = _jd.get_device(device_name)
            if _device is None:
                _device = _jd.get_device(devices[0]["name"])
                return f"Warning: Device '{device_name}' not found. Using '{devices[0]['name']}' instead."
        else:
            _device = _jd.get_device(devices[0]["name"])

        return f"Connected successfully. Device: {_device.name}. Available devices: {[d['name'] for d in devices]}"
    except Exception as e:
        _jd = None
        _device = None
        return f"Error connecting: {e}"



@mcp.tool()
def jd_disconnect() -> str:
    """Disconnect from My.JDownloader."""
    global _jd, _device
    if _jd is None:
        return "Not connected"
    try:
        _jd.disconnect()
        _jd = None
        _device = None
        return "Disconnected successfully"
    except Exception as e:
        return f"Error disconnecting: {e}"


@mcp.tool()
def jd_reconnect() -> str:
    """Reconnect to My.JDownloader (refresh session)."""
    global _jd
    if _jd is None:
        return "Error: Not connected. Call jd_connect first."
    try:
        _jd.reconnect()
        return "Reconnected successfully"
    except Exception as e:
        return f"Error reconnecting: {e}"


@mcp.tool()
def jd_list_devices() -> str:
    """List all JDownloader devices linked to the account."""
    global _jd
    if _jd is None:
        return "Error: Not connected. Call jd_connect first."
    try:
        _jd.update_devices()
        devices = _jd.list_devices()
        if not devices:
            return "No devices found"
        result = "Devices:\n"
        for d in devices:
            result += f"  - {d['name']} (id: {d.get('id', 'N/A')}, type: {d.get('type', 'N/A')})\n"
        return result
    except Exception as e:
        return f"Error listing devices: {e}"


@mcp.tool()
def jd_switch_device(device_name: str) -> str:
    """
    Switch to a different JDownloader device.

    Args:
        device_name: Name of the device to switch to
    """
    global _jd, _device
    if _jd is None:
        return "Error: Not connected. Call jd_connect first."
    try:
        _jd.update_devices()
        _device = _jd.get_device(device_name)
        return f"Switched to device: {_device.name}"
    except Exception as e:
        return f"Error switching device: {e}"



# ===========================================================================
# LINKGRABBER TOOLS (LinkCollector)
# ===========================================================================

@mcp.tool()
def jd_add_links(
    urls: str,
    package_name: Optional[str] = None,
    destination_folder: Optional[str] = None,
    autostart: bool = False,
    priority: str = "DEFAULT",
    extract_password: Optional[str] = None,
    download_password: Optional[str] = None,
    overwrite_packagizer: bool = False
) -> str:
    """
    Add links/URLs to the LinkCollector (Linkgrabber).

    Args:
        urls: URLs to add (space or newline separated for multiple)
        package_name: Custom package name (optional)
        destination_folder: Download destination path (optional)
        autostart: Whether to start download automatically (default: False)
        priority: Priority level: HIGHEST, HIGHER, HIGH, DEFAULT, LOWER
        extract_password: Password for extracting archives (optional)
        download_password: Password for download (optional)
        overwrite_packagizer: Override packagizer rules (default: False)
    """
    device = _ensure_connected()
    try:
        params = [{
            "autostart": autostart,
            "links": urls,
            "packageName": package_name,
            "extractPassword": extract_password,
            "priority": priority,
            "downloadPassword": download_password,
            "destinationFolder": destination_folder,
            "overwritePackagizerRules": overwrite_packagizer,
        }]
        result = device.linkgrabber.add_links(params)
        msg = f"Links added to LinkCollector"
        if package_name:
            msg += f" (package: '{package_name}')"
        if autostart:
            msg += " [autostart enabled]"
        else:
            msg += " [autostart disabled - review in JDownloader before starting]"
        return msg
    except Exception as e:
        return f"Error adding links: {e}"



@mcp.tool()
def jd_linkgrabber_query_packages(max_results: int = -1) -> str:
    """
    List all packages currently in the LinkCollector (Linkgrabber).

    Args:
        max_results: Maximum number of packages to return (-1 for all)
    """
    device = _ensure_connected()
    try:
        params = [{
            "bytesTotal": True,
            "childCount": True,
            "comment": True,
            "enabled": True,
            "hosts": True,
            "maxResults": max_results,
            "priority": True,
            "saveTo": True,
            "startAt": 0,
            "status": True,
        }]
        packages = device.linkgrabber.query_packages(params)
        if not packages:
            return "LinkCollector is empty (no packages)"

        result = f"LinkCollector: {len(packages)} package(s)\n"
        result += "-" * 50 + "\n"
        for p in packages:
            name = p.get("name", "Unknown")
            count = p.get("childCount", 0)
            size = _format_size(p.get("bytesTotal", 0))
            enabled = "enabled" if p.get("enabled", True) else "disabled"
            uuid = p.get("uuid", "")
            result += f"  [{uuid}] {name} ({count} links, {size}, {enabled})\n"
        return result
    except Exception as e:
        return f"Error querying packages: {e}"


@mcp.tool()
def jd_linkgrabber_query_links(
    package_uuids: Optional[str] = None,
    max_results: int = -1
) -> str:
    """
    List links in the LinkCollector with full details.

    Args:
        package_uuids: Comma-separated package UUIDs to filter (optional, all if empty)
        max_results: Maximum number of links to return (-1 for all)
    """
    device = _ensure_connected()
    try:
        params = [{
            "bytesTotal": True,
            "comment": True,
            "status": True,
            "enabled": True,
            "maxResults": max_results,
            "startAt": 0,
            "hosts": True,
            "url": True,
            "availability": True,
            "variantName": True,
            "variantID": True,
            "variants": True,
            "priority": True,
            "packageUUID": True,
        }]
        if package_uuids:
            params[0]["packageUUIDs"] = [int(x.strip()) for x in package_uuids.split(",")]

        links = device.linkgrabber.query_links(params)
        if not links:
            return "No links found in LinkCollector"

        result = f"LinkCollector: {len(links)} link(s)\n"
        result += "-" * 50 + "\n"
        for l in links:
            name = l.get("name", "Unknown")
            size = _format_size(l.get("bytesTotal", 0))
            avail = l.get("availability", "UNKNOWN")
            variant = l.get("variantName", "")
            uuid = l.get("uuid", "")
            pkg = l.get("packageUUID", "")
            result += f"  [{uuid}] {name}\n"
            result += f"      Size: {size} | Status: {avail} | Variant: {variant} | Pkg: {pkg}\n"
        return result
    except Exception as e:
        return f"Error querying links: {e}"



@mcp.tool()
def jd_linkgrabber_move_to_downloadlist(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Move packages/links from LinkCollector to the download list (starts them).

    Args:
        link_ids: Comma-separated link UUIDs to move (optional)
        package_ids: Comma-separated package UUIDs to move (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        if not lids and not pids:
            return "Error: Provide at least link_ids or package_ids"
        device.linkgrabber.move_to_downloadlist(lids, pids)
        return f"Moved to download list: {len(lids)} link(s), {len(pids)} package(s)"
    except Exception as e:
        return f"Error moving to download list: {e}"


@mcp.tool()
def jd_linkgrabber_move_to_new_package(
    link_ids: str,
    new_package_name: str,
    download_path: str = ""
) -> str:
    """
    Move links to a new package (effectively renaming/reorganizing).

    Args:
        link_ids: Comma-separated link UUIDs to move
        new_package_name: Name for the new package
        download_path: Download path for the new package (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")]
        device.linkgrabber.move_to_new_package(lids, [], new_package_name, download_path)
        return f"Moved {len(lids)} link(s) to new package: '{new_package_name}'"
    except Exception as e:
        return f"Error moving to new package: {e}"


@mcp.tool()
def jd_linkgrabber_rename_package(package_id: str, new_name: str) -> str:
    """
    Rename a package in the LinkCollector.

    Args:
        package_id: Package UUID to rename
        new_name: New name for the package
    """
    device = _ensure_connected()
    try:
        device.linkgrabber.rename_package(int(package_id), new_name)
        return f"Package {package_id} renamed to: '{new_name}'"
    except Exception as e:
        return f"Error renaming package: {e}"


@mcp.tool()
def jd_linkgrabber_rename_link(link_id: str, new_name: str) -> str:
    """
    Rename a link (file) in the LinkCollector.

    Args:
        link_id: Link UUID to rename
        new_name: New filename for the link
    """
    device = _ensure_connected()
    try:
        device.linkgrabber.rename_link(int(link_id), new_name)
        return f"Link {link_id} renamed to: '{new_name}'"
    except Exception as e:
        return f"Error renaming link: {e}"



@mcp.tool()
def jd_linkgrabber_set_priority(
    priority: str,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Set priority of links or packages in LinkCollector.

    Args:
        priority: Priority level: HIGHEST, HIGHER, HIGH, DEFAULT, LOWER
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.linkgrabber.set_priority(priority, lids, pids)
        return f"Priority set to {priority}"
    except Exception as e:
        return f"Error setting priority: {e}"


@mcp.tool()
def jd_linkgrabber_set_enabled(
    enabled: bool,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Enable or disable links/packages in LinkCollector.

    Args:
        enabled: True to enable, False to disable
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.linkgrabber.set_enabled(enabled, lids, pids)
        state = "enabled" if enabled else "disabled"
        return f"Items {state} successfully"
    except Exception as e:
        return f"Error setting enabled state: {e}"


@mcp.tool()
def jd_linkgrabber_get_variants(link_id: str) -> str:
    """
    Get available variants for a link (e.g., video/audio quality options).

    Args:
        link_id: Link UUID to get variants for
    """
    device = _ensure_connected()
    try:
        variants = device.linkgrabber.get_variants([int(link_id)])
        if not variants:
            return "No variants available for this link"
        result = f"Variants for link {link_id}:\n"
        for v in variants:
            result += f"  - {v.get('id', '?')}: {v.get('name', '?')}\n"
        return result
    except Exception as e:
        return f"Error getting variants: {e}"


@mcp.tool()
def jd_linkgrabber_cleanup(
    action: str = "DELETE_ALL",
    mode: str = "REMOVE_LINKS_ONLY",
    selection_type: str = "ALL",
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Clean up the LinkCollector.

    Args:
        action: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED, DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE
        mode: REMOVE_LINKS_AND_DELETE_FILES, REMOVE_LINKS_AND_RECYCLE_FILES, REMOVE_LINKS_ONLY
        selection_type: SELECTED, UNSELECTED, ALL, NONE
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.linkgrabber.cleanup(action, mode, selection_type, lids, pids)
        return f"Cleanup done: action={action}, mode={mode}, selection={selection_type}"
    except Exception as e:
        return f"Error cleaning up: {e}"



@mcp.tool()
def jd_linkgrabber_clear_list() -> str:
    """Clear the entire LinkCollector list."""
    device = _ensure_connected()
    try:
        device.linkgrabber.clear_list()
        return "LinkCollector cleared"
    except Exception as e:
        return f"Error clearing list: {e}"


@mcp.tool()
def jd_linkgrabber_remove_links(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Remove specific links/packages from LinkCollector.

    Args:
        link_ids: Comma-separated link UUIDs to remove (optional)
        package_ids: Comma-separated package UUIDs to remove (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.linkgrabber.remove_links(lids, pids)
        return f"Removed: {len(lids)} link(s), {len(pids)} package(s)"
    except Exception as e:
        return f"Error removing links: {e}"


@mcp.tool()
def jd_linkgrabber_add_container(container_type: str, content: str) -> str:
    """
    Add a container file (DLC, RSDF, CCF) to LinkCollector.

    Args:
        container_type: Type of container (e.g., 'DLC', 'RSDF', 'CCF')
        content: Container content (base64 encoded)
    """
    device = _ensure_connected()
    try:
        device.linkgrabber.add_container(container_type, content)
        return f"Container ({container_type}) added to LinkCollector"
    except Exception as e:
        return f"Error adding container: {e}"


@mcp.tool()
def jd_linkgrabber_is_collecting() -> str:
    """Check if the LinkCollector is currently processing/collecting links."""
    device = _ensure_connected()
    try:
        result = device.linkgrabber.is_collecting()
        if result:
            return "LinkCollector is currently collecting/processing links"
        return "LinkCollector is idle (not collecting)"
    except Exception as e:
        return f"Error checking collection status: {e}"


@mcp.tool()
def jd_linkgrabber_get_package_count() -> str:
    """Get the total number of packages in the LinkCollector."""
    device = _ensure_connected()
    try:
        count = device.linkgrabber.get_package_count()
        return f"Packages in LinkCollector: {count}"
    except Exception as e:
        return f"Error getting package count: {e}"



# ===========================================================================
# DOWNLOAD CONTROLLER TOOLS
# ===========================================================================

@mcp.tool()
def jd_start_downloads() -> str:
    """Start/resume all downloads in JDownloader."""
    device = _ensure_connected()
    try:
        device.downloadcontroller.start_downloads()
        return "Downloads started"
    except Exception as e:
        return f"Error starting downloads: {e}"


@mcp.tool()
def jd_stop_downloads() -> str:
    """Stop all downloads in JDownloader."""
    device = _ensure_connected()
    try:
        device.downloadcontroller.stop_downloads()
        return "Downloads stopped"
    except Exception as e:
        return f"Error stopping downloads: {e}"


@mcp.tool()
def jd_pause_downloads(pause: bool) -> str:
    """
    Pause or unpause downloads.

    Args:
        pause: True to pause, False to unpause
    """
    device = _ensure_connected()
    try:
        device.downloadcontroller.pause_downloads(pause)
        state = "paused" if pause else "unpaused"
        return f"Downloads {state}"
    except Exception as e:
        return f"Error pausing downloads: {e}"


@mcp.tool()
def jd_get_download_speed() -> str:
    """Get current download speed in bytes per second."""
    device = _ensure_connected()
    try:
        speed = device.downloadcontroller.get_speed_in_bytes()
        return f"Current speed: {_format_size(speed)}/s"
    except Exception as e:
        return f"Error getting speed: {e}"


@mcp.tool()
def jd_get_download_state() -> str:
    """Get current state of the download controller (RUNNING, STOPPED, PAUSE, etc.)."""
    device = _ensure_connected()
    try:
        state = device.downloadcontroller.get_current_state()
        return f"Download controller state: {state}"
    except Exception as e:
        return f"Error getting state: {e}"


@mcp.tool()
def jd_force_download(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Force download of specific links/packages (bypass queue order).

    Args:
        link_ids: Comma-separated link UUIDs to force (optional)
        package_ids: Comma-separated package UUIDs to force (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloadcontroller.force_download(lids, pids)
        return "Force download initiated"
    except Exception as e:
        return f"Error forcing download: {e}"



# ===========================================================================
# DOWNLOADS LIST TOOLS
# ===========================================================================

@mcp.tool()
def jd_downloads_query_packages(max_results: int = -1) -> str:
    """
    List all packages in the download list (active/completed downloads).

    Args:
        max_results: Maximum number of packages to return (-1 for all)
    """
    device = _ensure_connected()
    try:
        params = [{
            "bytesLoaded": True,
            "bytesTotal": True,
            "childCount": True,
            "comment": True,
            "enabled": True,
            "eta": True,
            "finished": True,
            "hosts": True,
            "maxResults": max_results,
            "priority": True,
            "running": True,
            "saveTo": True,
            "speed": True,
            "startAt": 0,
            "status": True,
        }]
        packages = device.downloads.query_packages(params)
        if not packages:
            return "Download list is empty"

        result = f"Downloads: {len(packages)} package(s)\n"
        result += "-" * 50 + "\n"
        for p in packages:
            name = p.get("name", "Unknown")
            loaded = p.get("bytesLoaded", 0)
            total = p.get("bytesTotal", 0)
            progress = (loaded / total * 100) if total > 0 else 0
            finished = p.get("finished", False)
            speed = _format_size(p.get("speed", 0))
            uuid = p.get("uuid", "")
            status = "DONE" if finished else f"{progress:.1f}%"
            result += f"  [{uuid}] {name}\n"
            result += f"      {_format_size(loaded)}/{_format_size(total)} ({status})"
            if not finished and p.get("speed", 0) > 0:
                result += f" @ {speed}/s"
            result += "\n"
        return result
    except Exception as e:
        return f"Error querying download packages: {e}"


@mcp.tool()
def jd_downloads_query_links(
    package_uuids: Optional[str] = None,
    max_results: int = -1
) -> str:
    """
    List links in the download list with progress details.

    Args:
        package_uuids: Comma-separated package UUIDs to filter (optional)
        max_results: Maximum number of links to return (-1 for all)
    """
    device = _ensure_connected()
    try:
        params = [{
            "addedDate": True,
            "bytesLoaded": True,
            "bytesTotal": True,
            "enabled": True,
            "eta": True,
            "finished": True,
            "host": True,
            "maxResults": max_results,
            "priority": True,
            "running": True,
            "speed": True,
            "startAt": 0,
            "status": True,
            "url": True,
        }]
        if package_uuids:
            params[0]["packageUUIDs"] = [int(x.strip()) for x in package_uuids.split(",")]

        links = device.downloads.query_links(params)
        if not links:
            return "No links in download list"

        result = f"Download links: {len(links)}\n"
        result += "-" * 50 + "\n"
        for l in links:
            name = l.get("name", "Unknown")
            loaded = l.get("bytesLoaded", 0)
            total = l.get("bytesTotal", 0)
            progress = (loaded / total * 100) if total > 0 else 0
            finished = l.get("finished", False)
            status = "DONE" if finished else f"{progress:.1f}%"
            result += f"  {name} [{status}] ({_format_size(loaded)}/{_format_size(total)})\n"
        return result
    except Exception as e:
        return f"Error querying download links: {e}"



@mcp.tool()
def jd_downloads_set_enabled(
    enabled: bool,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Enable or disable links/packages in the download list.

    Args:
        enabled: True to enable, False to disable
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloads.set_enabled(enabled, lids, pids)
        state = "enabled" if enabled else "disabled"
        return f"Download items {state}"
    except Exception as e:
        return f"Error setting enabled state: {e}"


@mcp.tool()
def jd_downloads_force_download(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Force download of specific items in the download list.

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloads.force_download(lids, pids)
        return "Force download initiated"
    except Exception as e:
        return f"Error forcing download: {e}"


@mcp.tool()
def jd_downloads_set_location(
    directory: str,
    package_ids: str
) -> str:
    """
    Set download directory for packages.

    Args:
        directory: Full path to download directory
        package_ids: Comma-separated package UUIDs
    """
    device = _ensure_connected()
    try:
        pids = [int(x.strip()) for x in package_ids.split(",")]
        device.downloads.set_dl_location(directory, pids)
        return f"Download location set to: {directory}"
    except Exception as e:
        return f"Error setting download location: {e}"


@mcp.tool()
def jd_downloads_remove_links(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Remove links/packages from the download list.

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloads.remove_links(lids, pids)
        return "Items removed from download list"
    except Exception as e:
        return f"Error removing from downloads: {e}"


@mcp.tool()
def jd_downloads_reset_links(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Reset links in the download list (re-download them).

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloads.reset_links(lids, pids)
        return "Links reset successfully (will re-download)"
    except Exception as e:
        return f"Error resetting links: {e}"


@mcp.tool()
def jd_downloads_move_to_new_package(
    link_ids: str,
    new_package_name: str,
    download_path: str = ""
) -> str:
    """
    Move download links to a new package in the download list.

    Args:
        link_ids: Comma-separated link UUIDs to move
        new_package_name: Name for the new package
        download_path: Download path (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")]
        device.downloads.move_to_new_package(lids, [], new_package_name, download_path)
        return f"Moved {len(lids)} link(s) to new package: '{new_package_name}'"
    except Exception as e:
        return f"Error moving to new package: {e}"


@mcp.tool()
def jd_downloads_cleanup(
    action: str = "DELETE_FINISHED",
    mode: str = "REMOVE_LINKS_ONLY",
    selection_type: str = "ALL",
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Clean up the download list.

    Args:
        action: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED, DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE
        mode: REMOVE_LINKS_AND_DELETE_FILES, REMOVE_LINKS_AND_RECYCLE_FILES, REMOVE_LINKS_ONLY
        selection_type: SELECTED, UNSELECTED, ALL, NONE
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.downloads.cleanup(action, mode, selection_type, lids, pids)
        return f"Download list cleanup done: action={action}, mode={mode}"
    except Exception as e:
        return f"Error cleaning downloads: {e}"



# ===========================================================================
# CAPTCHA TOOLS
# ===========================================================================

@mcp.tool()
def jd_captcha_list() -> str:
    """List all pending captchas waiting to be solved."""
    device = _ensure_connected()
    try:
        captchas = device.captcha.list()
        if not captchas:
            return "No pending captchas"
        result = f"Pending captchas: {len(captchas)}\n"
        for c in captchas:
            result += f"  - ID: {c.get('id', '?')}, Type: {c.get('type', '?')}, Hoster: {c.get('hoster', '?')}\n"
        return result
    except Exception as e:
        return f"Error listing captchas: {e}"


@mcp.tool()
def jd_captcha_get(captcha_id: int) -> str:
    """
    Get captcha image data (base64 encoded).

    Args:
        captcha_id: ID of the captcha to retrieve
    """
    device = _ensure_connected()
    try:
        data = device.captcha.get(captcha_id)
        if data:
            return f"Captcha {captcha_id} image (base64): {data[:100]}... (truncated, full length: {len(data)} chars)"
        return f"No data returned for captcha {captcha_id}"
    except Exception as e:
        return f"Error getting captcha: {e}"


@mcp.tool()
def jd_captcha_solve(captcha_id: int, solution: str) -> str:
    """
    Submit a captcha solution.

    Args:
        captcha_id: ID of the captcha to solve
        solution: The captcha solution text
    """
    device = _ensure_connected()
    try:
        device.captcha.solve(captcha_id, solution)
        return f"Captcha {captcha_id} solved with: '{solution}'"
    except Exception as e:
        return f"Error solving captcha: {e}"



# ===========================================================================
# ACCOUNTS TOOLS
# ===========================================================================

@mcp.tool()
def jd_accounts_list() -> str:
    """List all premium hoster accounts configured in JDownloader."""
    device = _ensure_connected()
    try:
        accounts = device.accounts.list_accounts()
        if not accounts:
            return "No accounts configured"
        result = f"Accounts: {len(accounts)}\n"
        for a in accounts:
            hostname = a.get("hostname", "?")
            username = a.get("username", "?")
            enabled = a.get("enabled", False)
            valid = a.get("valid", False)
            traffic = a.get("trafficLeft", 0)
            status = "enabled" if enabled else "disabled"
            validity = "valid" if valid else "INVALID"
            result += f"  - [{a.get('uuid', '?')}] {hostname} ({username}) [{status}, {validity}]"
            if traffic:
                result += f" Traffic left: {_format_size(traffic)}"
            result += "\n"
        return result
    except Exception as e:
        return f"Error listing accounts: {e}"


@mcp.tool()
def jd_accounts_add(premium_hoster: str, username: str, password: str) -> str:
    """
    Add a premium hoster account.

    Args:
        premium_hoster: Hoster name (e.g., 'mega.nz', 'rapidgator.net')
        username: Account username/email
        password: Account password
    """
    device = _ensure_connected()
    try:
        device.accounts.add_account(premium_hoster, username, password)
        return f"Account added for {premium_hoster} ({username})"
    except Exception as e:
        return f"Error adding account: {e}"


@mcp.tool()
def jd_accounts_remove(account_ids: str) -> str:
    """
    Remove premium hoster accounts.

    Args:
        account_ids: Comma-separated account UUIDs to remove
    """
    device = _ensure_connected()
    try:
        ids = [int(x.strip()) for x in account_ids.split(",")]
        device.accounts.remove_accounts(ids)
        return f"Removed {len(ids)} account(s)"
    except Exception as e:
        return f"Error removing accounts: {e}"


@mcp.tool()
def jd_accounts_enable(account_ids: str) -> str:
    """
    Enable premium hoster accounts.

    Args:
        account_ids: Comma-separated account UUIDs to enable
    """
    device = _ensure_connected()
    try:
        ids = [int(x.strip()) for x in account_ids.split(",")]
        device.accounts.enable_accounts(ids)
        return f"Enabled {len(ids)} account(s)"
    except Exception as e:
        return f"Error enabling accounts: {e}"


@mcp.tool()
def jd_accounts_disable(account_ids: str) -> str:
    """
    Disable premium hoster accounts.

    Args:
        account_ids: Comma-separated account UUIDs to disable
    """
    device = _ensure_connected()
    try:
        ids = [int(x.strip()) for x in account_ids.split(",")]
        device.accounts.disable_accounts(ids)
        return f"Disabled {len(ids)} account(s)"
    except Exception as e:
        return f"Error disabling accounts: {e}"


@mcp.tool()
def jd_accounts_refresh(account_ids: str) -> str:
    """
    Refresh/validate premium hoster accounts.

    Args:
        account_ids: Comma-separated account UUIDs to refresh
    """
    device = _ensure_connected()
    try:
        ids = [int(x.strip()) for x in account_ids.split(",")]
        device.accounts.refresh_accounts(ids)
        return f"Refreshed {len(ids)} account(s)"
    except Exception as e:
        return f"Error refreshing accounts: {e}"


@mcp.tool()
def jd_accounts_list_premium_hosters() -> str:
    """List all supported premium hosters."""
    device = _ensure_connected()
    try:
        hosters = device.accounts.list_premium_hoster()
        if not hosters:
            return "No premium hosters available"
        result = f"Premium hosters ({len(hosters)}):\n"
        for h in hosters:
            result += f"  - {h}\n"
        return result
    except Exception as e:
        return f"Error listing hosters: {e}"


@mcp.tool()
def jd_accounts_add_basic_auth(
    auth_type: str,
    hostmask: str,
    username: str,
    password: str
) -> str:
    """
    Add a basic auth entry (HTTP/FTP authentication).

    Args:
        auth_type: Type of auth: 'HTTP' or 'FTP'
        hostmask: Host mask pattern (e.g., '*.example.com')
        username: Username
        password: Password
    """
    device = _ensure_connected()
    try:
        result = device.accounts.add_basic_auth(auth_type, hostmask, username, password)
        return f"Basic auth added for {hostmask} (type: {auth_type}, id: {result})"
    except Exception as e:
        return f"Error adding basic auth: {e}"


@mcp.tool()
def jd_accounts_list_basic_auth() -> str:
    """List all basic auth entries."""
    device = _ensure_connected()
    try:
        auths = device.accounts.list_basic_auth()
        if not auths:
            return "No basic auth entries"
        result = f"Basic auth entries: {len(auths)}\n"
        for a in auths:
            result += f"  - [{a.get('id', '?')}] {a.get('type', '?')}://{a.get('username', '?')}@{a.get('hostmask', '?')}\n"
        return result
    except Exception as e:
        return f"Error listing basic auth: {e}"



# ===========================================================================
# SYSTEM TOOLS
# ===========================================================================

@mcp.tool()
def jd_system_get_storage_info() -> str:
    """Get storage/disk information from the JDownloader device."""
    device = _ensure_connected()
    try:
        info = device.system.get_storage_info()
        if not info:
            return "No storage info available"
        result = "Storage info:\n"
        for s in info:
            path = s.get("path", "?")
            total = _format_size(s.get("size", 0))
            free = _format_size(s.get("free", 0))
            result += f"  {path}: {free} free / {total} total\n"
        return result
    except Exception as e:
        return f"Error getting storage info: {e}"


@mcp.tool()
def jd_system_restart() -> str:
    """Restart JDownloader application."""
    device = _ensure_connected()
    try:
        device.system.restart_jd()
        return "JDownloader restart initiated"
    except Exception as e:
        return f"Error restarting JDownloader: {e}"


@mcp.tool()
def jd_system_exit() -> str:
    """Exit/close JDownloader application."""
    device = _ensure_connected()
    try:
        device.system.exit_jd()
        return "JDownloader exit initiated"
    except Exception as e:
        return f"Error exiting JDownloader: {e}"


@mcp.tool()
def jd_system_hibernate() -> str:
    """Hibernate the OS (where JDownloader runs)."""
    device = _ensure_connected()
    try:
        device.system.hibernate_os()
        return "OS hibernate initiated"
    except Exception as e:
        return f"Error hibernating: {e}"


@mcp.tool()
def jd_system_shutdown(force: bool = False) -> str:
    """
    Shutdown the OS (where JDownloader runs).

    Args:
        force: Force shutdown without waiting for downloads
    """
    device = _ensure_connected()
    try:
        device.system.shutdown_os(force)
        return f"OS shutdown initiated (force={force})"
    except Exception as e:
        return f"Error shutting down: {e}"


@mcp.tool()
def jd_system_standby() -> str:
    """Put the OS in standby mode."""
    device = _ensure_connected()
    try:
        device.system.standby_os()
        return "OS standby initiated"
    except Exception as e:
        return f"Error entering standby: {e}"



# ===========================================================================
# CONFIG TOOLS
# ===========================================================================

@mcp.tool()
def jd_config_list(pattern: str = "") -> str:
    """
    List all advanced configuration entries (or filter by pattern).

    Args:
        pattern: Filter pattern (e.g., 'download' to show download-related config)
    """
    device = _ensure_connected()
    try:
        params = [{
            "configInterface": "",
            "defaultValues": True,
            "description": True,
            "enumInfo": True,
            "includeExtensions": True,
            "pattern": pattern,
            "values": True,
        }]
        configs = device.config.query(params)
        if not configs:
            return "No configuration entries found"
        result = f"Config entries ({len(configs)}):\n"
        for c in configs[:50]:  # Limit output
            key = c.get("key", "?")
            value = c.get("value", "?")
            desc = c.get("docs", c.get("description", ""))
            result += f"  {c.get('interfaceName', '?')}.{key} = {value}\n"
            if desc:
                result += f"      ({desc})\n"
        if len(configs) > 50:
            result += f"\n  ... and {len(configs) - 50} more entries. Use a pattern to filter."
        return result
    except Exception as e:
        return f"Error listing config: {e}"


@mcp.tool()
def jd_config_get(interface_name: str, key: str, storage: str = "null") -> str:
    """
    Get a specific configuration value.

    Args:
        interface_name: Config interface name (e.g., 'org.jdownloader.settings.GeneralSettings')
        key: Configuration key name
        storage: Storage location ('null' for default, or 'cfg/' + interfaceName)
    """
    device = _ensure_connected()
    try:
        value = device.config.get(interface_name, storage, key)
        return f"{interface_name}.{key} = {json.dumps(value)}"
    except Exception as e:
        return f"Error getting config: {e}"


@mcp.tool()
def jd_config_set(interface_name: str, key: str, value: str, storage: str = "null") -> str:
    """
    Set a configuration value.

    Args:
        interface_name: Config interface name
        key: Configuration key name
        value: New value (as JSON string, e.g., '"text"', '123', 'true')
        storage: Storage location ('null' for default)
    """
    device = _ensure_connected()
    try:
        parsed_value = json.loads(value)
        device.config.set(interface_name, storage, key, parsed_value)
        return f"Config set: {interface_name}.{key} = {value}"
    except json.JSONDecodeError:
        return f"Error: value must be valid JSON (e.g., '\"text\"', '123', 'true')"
    except Exception as e:
        return f"Error setting config: {e}"


@mcp.tool()
def jd_config_reset(interface_name: str, key: str, storage: str = "null") -> str:
    """
    Reset a configuration value to default.

    Args:
        interface_name: Config interface name
        key: Configuration key name
        storage: Storage location ('null' for default)
    """
    device = _ensure_connected()
    try:
        device.config.reset(interface_name, storage, key)
        return f"Config reset: {interface_name}.{key}"
    except Exception as e:
        return f"Error resetting config: {e}"



# ===========================================================================
# EXTENSIONS TOOLS
# ===========================================================================

@mcp.tool()
def jd_extensions_list(pattern: str = "") -> str:
    """
    List all available JDownloader extensions/plugins.

    Args:
        pattern: Filter pattern (optional)
    """
    device = _ensure_connected()
    try:
        params = [{
            "configInterface": True,
            "description": True,
            "enabled": True,
            "iconKey": True,
            "name": True,
            "pattern": pattern,
            "installed": True,
        }]
        extensions = device.extension.list(params)
        if not extensions:
            return "No extensions found"
        result = f"Extensions ({len(extensions)}):\n"
        for ext in extensions:
            name = ext.get("name", "?")
            desc = ext.get("description", "")
            enabled = ext.get("enabled", False)
            installed = ext.get("installed", False)
            status = []
            if installed:
                status.append("installed")
            if enabled:
                status.append("enabled")
            result += f"  - {name} [{', '.join(status) or 'not installed'}]\n"
            if desc:
                result += f"      {desc}\n"
        return result
    except Exception as e:
        return f"Error listing extensions: {e}"


@mcp.tool()
def jd_extensions_install(extension_id: str) -> str:
    """
    Install a JDownloader extension.

    Args:
        extension_id: Extension class ID to install
    """
    device = _ensure_connected()
    try:
        device.extension.install(extension_id)
        return f"Extension '{extension_id}' installed"
    except Exception as e:
        return f"Error installing extension: {e}"


@mcp.tool()
def jd_extensions_set_enabled(extension_id: str, enabled: bool) -> str:
    """
    Enable or disable a JDownloader extension.

    Args:
        extension_id: Extension class ID
        enabled: True to enable, False to disable
    """
    device = _ensure_connected()
    try:
        device.extension.setEnabled(extension_id, enabled)
        state = "enabled" if enabled else "disabled"
        return f"Extension '{extension_id}' {state}"
    except Exception as e:
        return f"Error setting extension state: {e}"



# ===========================================================================
# DIALOG TOOLS
# ===========================================================================

@mcp.tool()
def jd_dialogs_list() -> str:
    """List all open dialogs/popups in JDownloader."""
    device = _ensure_connected()
    try:
        dialogs = device.dialog.list()
        if not dialogs:
            return "No open dialogs"
        result = f"Open dialogs: {len(dialogs)}\n"
        for d in dialogs:
            result += f"  - ID: {d}\n"
        return result
    except Exception as e:
        return f"Error listing dialogs: {e}"


@mcp.tool()
def jd_dialogs_get(dialog_id: int) -> str:
    """
    Get details of a dialog.

    Args:
        dialog_id: Dialog ID to retrieve
    """
    device = _ensure_connected()
    try:
        dialog = device.dialog.get(dialog_id, icon=False, properties=True)
        return f"Dialog {dialog_id}:\n{json.dumps(dialog, indent=2, ensure_ascii=False)}"
    except Exception as e:
        return f"Error getting dialog: {e}"


@mcp.tool()
def jd_dialogs_answer(dialog_id: int, response_data: str = "{}") -> str:
    """
    Answer/respond to a dialog.

    Args:
        dialog_id: Dialog ID to answer
        response_data: JSON string with the response data (depends on dialog type)
    """
    device = _ensure_connected()
    try:
        data = json.loads(response_data)
        device.dialog.answer(dialog_id, data)
        return f"Dialog {dialog_id} answered"
    except json.JSONDecodeError:
        return "Error: response_data must be valid JSON"
    except Exception as e:
        return f"Error answering dialog: {e}"


# ===========================================================================
# TOOLBAR / SPEED LIMIT TOOLS
# ===========================================================================

@mcp.tool()
def jd_toolbar_status() -> str:
    """Get JDownloader toolbar status (speed limit, etc.)."""
    device = _ensure_connected()
    try:
        status = device.toolbar.get_status()
        result = "Toolbar status:\n"
        result += f"  Speed limit active: {status.get('limit', False)}\n"
        result += f"  Downloads running: {status.get('running', False)}\n"
        result += f"  Reconnect: {status.get('reconnect', False)}\n"
        result += f"  Clipboard: {status.get('clipboard', False)}\n"
        result += f"  Premium: {status.get('premium', False)}\n"
        return result
    except Exception as e:
        return f"Error getting toolbar status: {e}"


@mcp.tool()
def jd_speed_limit_enable() -> str:
    """Enable download speed limit."""
    device = _ensure_connected()
    try:
        device.toolbar.enable_downloadSpeedLimit()
        return "Speed limit enabled"
    except Exception as e:
        return f"Error enabling speed limit: {e}"


@mcp.tool()
def jd_speed_limit_disable() -> str:
    """Disable download speed limit."""
    device = _ensure_connected()
    try:
        device.toolbar.disable_downloadSpeedLimit()
        return "Speed limit disabled"
    except Exception as e:
        return f"Error disabling speed limit: {e}"



# ===========================================================================
# UPDATE TOOLS
# ===========================================================================

@mcp.tool()
def jd_update_check() -> str:
    """Check if a JDownloader update is available."""
    device = _ensure_connected()
    try:
        device.update.run_update_check()
        available = device.update.is_update_available()
        if available:
            return "Update available! Use jd_update_restart to install."
        return "JDownloader is up to date"
    except Exception as e:
        return f"Error checking updates: {e}"


@mcp.tool()
def jd_update_restart() -> str:
    """Restart JDownloader and install available updates."""
    device = _ensure_connected()
    try:
        device.update.restart_and_update()
        return "JDownloader restarting to install updates..."
    except Exception as e:
        return f"Error updating: {e}"


# ===========================================================================
# RECONNECT TOOL
# ===========================================================================

@mcp.tool()
def jd_reconnect() -> str:
    """Trigger internet reconnect to get a new IP address."""
    device = _ensure_connected()
    try:
        device.reconnect.do_reconnect()
        return "Internet reconnect triggered (new IP)"
    except Exception as e:
        return f"Error reconnecting: {e}"


# ===========================================================================
# JD INFO TOOLS
# ===========================================================================

@mcp.tool()
def jd_get_version() -> str:
    """Get JDownloader core revision/version."""
    device = _ensure_connected()
    try:
        revision = device.jd.get_core_revision()
        return f"JDownloader core revision: {revision}"
    except Exception as e:
        return f"Error getting version: {e}"



# ===========================================================================
# CONVENIENCE / HIGH-LEVEL TOOLS
# ===========================================================================

@mcp.tool()
def jd_get_overview() -> str:
    """
    Get a complete overview of the current JDownloader state:
    download controller state, speed, LinkCollector count, and download list summary.
    """
    device = _ensure_connected()
    try:
        result = "=== JDownloader Overview ===\n\n"

        # Controller state
        state = device.downloadcontroller.get_current_state()
        speed = device.downloadcontroller.get_speed_in_bytes()
        result += f"Controller: {state} | Speed: {_format_size(speed)}/s\n\n"

        # LinkCollector
        try:
            pkg_count = device.linkgrabber.get_package_count()
            result += f"LinkCollector: {pkg_count} package(s)\n"
        except:
            result += "LinkCollector: (unable to query)\n"

        # Downloads
        try:
            dl_packages = device.downloads.query_packages([{
                "bytesLoaded": True,
                "bytesTotal": True,
                "childCount": True,
                "finished": True,
                "maxResults": -1,
                "running": True,
                "speed": True,
                "startAt": 0,
            }])
            if dl_packages:
                total_pkgs = len(dl_packages)
                finished = sum(1 for p in dl_packages if p.get("finished"))
                running = sum(1 for p in dl_packages if p.get("running"))
                total_size = sum(p.get("bytesTotal", 0) for p in dl_packages)
                total_loaded = sum(p.get("bytesLoaded", 0) for p in dl_packages)
                result += f"\nDownloads: {total_pkgs} package(s)\n"
                result += f"  Running: {running} | Finished: {finished} | Pending: {total_pkgs - finished - running}\n"
                result += f"  Progress: {_format_size(total_loaded)} / {_format_size(total_size)}\n"
            else:
                result += "\nDownloads: empty\n"
        except:
            result += "\nDownloads: (unable to query)\n"

        # Captchas
        try:
            captchas = device.captcha.list()
            if captchas:
                result += f"\nPending captchas: {len(captchas)}\n"
        except:
            pass

        return result
    except Exception as e:
        return f"Error getting overview: {e}"


@mcp.tool()
def jd_linkgrabber_get_download_urls(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Get the actual download URLs for links in the LinkCollector.

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        urls = device.linkgrabber.get_download_urls(lids, pids, [])
        if not urls:
            return "No download URLs found"
        result = "Download URLs:\n"
        if isinstance(urls, dict):
            for key, val in urls.items():
                result += f"  {key}: {val}\n"
        else:
            result += json.dumps(urls, indent=2)
        return result
    except Exception as e:
        return f"Error getting download URLs: {e}"



# ===========================================================================
# EXTRACTION TOOLS (not in myjdapi, using device.action directly)
# ===========================================================================

@mcp.tool()
def jd_extraction_get_archive_info(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Get archive information for links/packages (extraction status, passwords, etc.).

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        result = device.action("/extraction/getArchiveInfo", [lids, pids])
        if not result:
            return "No archive info found"
        output = "Archive info:\n"
        if isinstance(result, list):
            for arch in result:
                output += f"  - ID: {arch.get('archiveId', '?')}\n"
                output += f"    Name: {arch.get('name', '?')}\n"
                output += f"    Type: {arch.get('type', '?')}\n"
                output += f"    Status: {arch.get('controllerStatus', 'N/A')}\n"
                output += f"    Password protected: {arch.get('passwordProtected', False)}\n"
        else:
            output += json.dumps(result, indent=2, ensure_ascii=False)
        return output
    except Exception as e:
        return f"Error getting archive info: {e}"


@mcp.tool()
def jd_extraction_get_queue() -> str:
    """Get the current extraction queue."""
    device = _ensure_connected()
    try:
        result = device.action("/extraction/getQueue")
        if not result:
            return "Extraction queue is empty"
        output = f"Extraction queue ({len(result)} item(s)):\n"
        for item in result:
            output += f"  - {item.get('archiveId', '?')}: {item.get('name', '?')} [{item.get('controllerStatus', '?')}]\n"
        return output
    except Exception as e:
        return f"Error getting extraction queue: {e}"


@mcp.tool()
def jd_extraction_cancel(controller_id: str) -> str:
    """
    Cancel an ongoing extraction.

    Args:
        controller_id: Archive controller ID to cancel
    """
    device = _ensure_connected()
    try:
        result = device.action("/extraction/cancelExtraction", [controller_id])
        return f"Extraction cancelled: {controller_id}"
    except Exception as e:
        return f"Error cancelling extraction: {e}"


@mcp.tool()
def jd_extraction_add_archive_password(password: str) -> str:
    """
    Add a password to JDownloader's extraction password list.

    Args:
        password: Password to add
    """
    device = _ensure_connected()
    try:
        device.action("/extraction/addArchivePassword", [password])
        return f"Archive password added"
    except Exception as e:
        return f"Error adding archive password: {e}"


@mcp.tool()
def jd_extraction_set_archive_passwords(archive_id: str, passwords: str) -> str:
    """
    Set passwords for a specific archive.

    Args:
        archive_id: Archive ID
        passwords: Comma-separated list of passwords to try
    """
    device = _ensure_connected()
    try:
        pwd_list = [p.strip() for p in passwords.split(",")]
        device.action("/extraction/setArchivePasswords", [archive_id, pwd_list])
        return f"Passwords set for archive {archive_id}"
    except Exception as e:
        return f"Error setting archive passwords: {e}"


@mcp.tool()
def jd_extraction_start(
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Start extraction for specified links/packages.

    Args:
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.action("/extraction/startExtractionNow", [lids, pids])
        return "Extraction started"
    except Exception as e:
        return f"Error starting extraction: {e}"


# ===========================================================================
# CAPTCHA FORWARD TOOLS (not in myjdapi)
# ===========================================================================

@mcp.tool()
def jd_captcha_forward_create_job(
    hoster: str,
    captcha_type: str,
    data: str
) -> str:
    """
    Create a captcha forwarding job (send captcha to external solver).

    Args:
        hoster: Hoster name that generated the captcha
        captcha_type: Type of captcha (e.g., 'image', 'recaptchav2', 'hcaptcha')
        data: Captcha data (base64 image or site key depending on type)
    """
    device = _ensure_connected()
    try:
        result = device.action("/captchaforward/createJobRecaptchaV2", [hoster, captcha_type, data])
        return f"Captcha forward job created: {result}"
    except Exception as e:
        return f"Error creating captcha forward job: {e}"


@mcp.tool()
def jd_captcha_forward_get_result(job_id: int) -> str:
    """
    Get the result of a captcha forwarding job.

    Args:
        job_id: Job ID returned by create_job
    """
    device = _ensure_connected()
    try:
        result = device.action("/captchaforward/getResult", [job_id])
        if result:
            return f"Captcha forward result: {result}"
        return f"No result yet for job {job_id} (still processing)"
    except Exception as e:
        return f"Error getting captcha forward result: {e}"


# ===========================================================================
# LINK CRAWLER TOOLS (not in myjdapi)
# ===========================================================================

@mcp.tool()
def jd_linkcrawler_is_crawling() -> str:
    """Check if the link crawler is currently active/crawling."""
    device = _ensure_connected()
    try:
        result = device.action("/linkcrawler/isCrawling")
        if result:
            return "Link crawler is active (crawling)"
        return "Link crawler is idle"
    except Exception as e:
        return f"Error checking crawler status: {e}"


# ===========================================================================
# DOWNLOADS V2 EXTRA METHODS (not in myjdapi)
# ===========================================================================

@mcp.tool()
def jd_downloads_set_comment(
    comment: str,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Set a comment on download links or packages.

    Args:
        comment: Comment text to set
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.action("/downloadsV2/setComment", [comment, lids, pids])
        return f"Comment set: '{comment}'"
    except Exception as e:
        return f"Error setting comment: {e}"


@mcp.tool()
def jd_downloads_set_priority(
    priority: str,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Set priority of links or packages in the download list.

    Args:
        priority: Priority level: HIGHEST, HIGHER, HIGH, DEFAULT, LOWER
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.action("/downloadsV2/setPriority", [priority, lids, pids])
        return f"Download priority set to {priority}"
    except Exception as e:
        return f"Error setting priority: {e}"


@mcp.tool()
def jd_downloads_rename_link(link_id: str, new_name: str) -> str:
    """
    Rename a link (file) in the download list.

    Args:
        link_id: Link UUID to rename
        new_name: New filename
    """
    device = _ensure_connected()
    try:
        device.action("/downloadsV2/renameLink", [int(link_id), new_name])
        return f"Download link {link_id} renamed to: '{new_name}'"
    except Exception as e:
        return f"Error renaming download link: {e}"


@mcp.tool()
def jd_downloads_rename_package(package_id: str, new_name: str) -> str:
    """
    Rename a package in the download list.

    Args:
        package_id: Package UUID to rename
        new_name: New package name
    """
    device = _ensure_connected()
    try:
        device.action("/downloadsV2/renamePackage", [int(package_id), new_name])
        return f"Download package {package_id} renamed to: '{new_name}'"
    except Exception as e:
        return f"Error renaming download package: {e}"


@mcp.tool()
def jd_downloads_set_download_password(
    link_ids: str,
    password: str
) -> str:
    """
    Set download password for links.

    Args:
        link_ids: Comma-separated link UUIDs
        password: Download password
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")]
        device.action("/downloadsV2/setDownloadPassword", [lids, password])
        return f"Download password set for {len(lids)} link(s)"
    except Exception as e:
        return f"Error setting download password: {e}"


@mcp.tool()
def jd_downloads_move_links(
    link_ids: str,
    after_link_id: str = "",
    dest_package_id: str = ""
) -> str:
    """
    Move links within the download list (reorder or move between packages).

    Args:
        link_ids: Comma-separated link UUIDs to move
        after_link_id: Link UUID after which to place (empty for beginning)
        dest_package_id: Destination package UUID
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")]
        after = int(after_link_id) if after_link_id else -1
        dest = int(dest_package_id) if dest_package_id else -1
        device.action("/downloadsV2/moveLinks", [lids, after, dest])
        return f"Moved {len(lids)} link(s)"
    except Exception as e:
        return f"Error moving links: {e}"


@mcp.tool()
def jd_downloads_move_packages(
    package_ids: str,
    after_package_id: str = ""
) -> str:
    """
    Move/reorder packages in the download list.

    Args:
        package_ids: Comma-separated package UUIDs to move
        after_package_id: Package UUID after which to place (empty for beginning)
    """
    device = _ensure_connected()
    try:
        pids = [int(x.strip()) for x in package_ids.split(",")]
        after = int(after_package_id) if after_package_id else -1
        device.action("/downloadsV2/movePackages", [pids, after])
        return f"Moved {len(pids)} package(s)"
    except Exception as e:
        return f"Error moving packages: {e}"


# ===========================================================================
# LINKGRABBER V2 EXTRA METHODS (not in myjdapi)
# ===========================================================================

@mcp.tool()
def jd_linkgrabber_set_comment(
    comment: str,
    link_ids: Optional[str] = None,
    package_ids: Optional[str] = None
) -> str:
    """
    Set a comment on links or packages in the LinkCollector.

    Args:
        comment: Comment text to set
        link_ids: Comma-separated link UUIDs (optional)
        package_ids: Comma-separated package UUIDs (optional)
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")] if link_ids else []
        pids = [int(x.strip()) for x in package_ids.split(",")] if package_ids else []
        device.action("/linkgrabberv2/setComment", [comment, lids, pids])
        return f"Comment set: '{comment}'"
    except Exception as e:
        return f"Error setting comment: {e}"


@mcp.tool()
def jd_linkgrabber_set_download_directory(
    directory: str,
    package_ids: str
) -> str:
    """
    Set download directory for packages in the LinkCollector.

    Args:
        directory: Full path to download directory
        package_ids: Comma-separated package UUIDs
    """
    device = _ensure_connected()
    try:
        pids = [int(x.strip()) for x in package_ids.split(",")]
        device.action("/linkgrabberv2/setDownloadDirectory", [directory, pids])
        return f"Download directory set to: {directory}"
    except Exception as e:
        return f"Error setting download directory: {e}"


@mcp.tool()
def jd_linkgrabber_set_download_password(
    link_ids: str,
    password: str
) -> str:
    """
    Set download password for links in the LinkCollector.

    Args:
        link_ids: Comma-separated link UUIDs
        password: Download password
    """
    device = _ensure_connected()
    try:
        lids = [int(x.strip()) for x in link_ids.split(",")]
        device.action("/linkgrabberv2/setDownloadPassword", [lids, password])
        return f"Download password set for {len(lids)} link(s) in LinkCollector"
    except Exception as e:
        return f"Error setting download password: {e}"


# ===========================================================================
# JD NAMESPACE EXTRA METHODS (not in myjdapi)
# ===========================================================================

@mcp.tool()
def jd_get_uptime() -> str:
    """Get JDownloader uptime in milliseconds."""
    device = _ensure_connected()
    try:
        uptime = device.action("/jd/uptime")
        if uptime:
            seconds = uptime / 1000
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"JDownloader uptime: {hours}h {minutes}m ({uptime}ms)"
        return "Unable to get uptime"
    except Exception as e:
        return f"Error getting uptime: {e}"


@mcp.tool()
def jd_get_timestamp() -> str:
    """Get current timestamp from JDownloader."""
    device = _ensure_connected()
    try:
        ts = device.action("/jd/timestamp")
        return f"JDownloader timestamp: {ts}"
    except Exception as e:
        return f"Error getting timestamp: {e}"


@mcp.tool()
def jd_do_refresh_plugins() -> str:
    """Force refresh of all JDownloader plugins (hoster/decrypter plugins)."""
    device = _ensure_connected()
    try:
        device.action("/jd/doRefreshPlugins")
        return "Plugins refreshed"
    except Exception as e:
        return f"Error refreshing plugins: {e}"


# ===========================================================================
# RAW API TOOL (for any endpoint not covered above)
# ===========================================================================

@mcp.tool()
def jd_raw_api_call(
    endpoint: str,
    params_json: str = "null"
) -> str:
    """
    Make a raw API call to any JDownloader endpoint.
    Use this for endpoints not covered by specific tools.

    Args:
        endpoint: API path (e.g., '/downloadsV2/queryLinks', '/extraction/getQueue')
        params_json: JSON string with parameters (e.g., '[[1234], [5678]]' or 'null')
    """
    device = _ensure_connected()
    try:
        if params_json and params_json != "null":
            params = json.loads(params_json)
        else:
            params = None
        result = device.action(endpoint, params)
        if result is None:
            return f"Call to {endpoint} returned null/void"
        return f"Result from {endpoint}:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    except json.JSONDecodeError as e:
        return f"Error: params_json must be valid JSON - {e}"
    except Exception as e:
        return f"Error calling {endpoint}: {e}"


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
