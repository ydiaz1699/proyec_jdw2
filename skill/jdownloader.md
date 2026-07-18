# JDownloader API - Kiro Skill

## Overview

This skill provides complete documentation for controlling JDownloader remotely
via the My.JDownloader API (myjdapi Python library v1.1.10).

Use this reference when generating code that interacts with JDownloader for:
- Adding download links
- Managing the LinkCollector (Linkgrabber)
- Controlling downloads (start/stop/pause)
- Managing premium accounts
- Solving captchas
- System operations (restart, shutdown)
- Configuration management

## Prerequisites

```bash
pip install myjdapi
```

**Environment variables (recommended):**
```
JD_EMAIL=your_myjdownloader_email
JD_PASSWORD=your_myjdownloader_password
JD_DEVICE_NAME=optional_device_name
```

## Connection Pattern

```python
import myjdapi

jd = myjdapi.Myjdapi()
jd.set_app_key("my-app-name")
jd.connect(email, password)
jd.update_devices()
device = jd.get_device("device_name")  # or first device

# ... use device ...

jd.disconnect()
```

**Important:** Always disconnect when done. Use try/finally.

---


## Module Reference

### 1. Linkgrabber (LinkCollector)

The Linkgrabber holds links before they are moved to the download list.
Access: `device.linkgrabber`

#### add_links(params)
Add URLs to the LinkCollector.

```python
device.linkgrabber.add_links([{
    "autostart": False,        # Don't start download automatically
    "links": "https://...",    # URL(s) - space/newline separated for multiple
    "packageName": "My Pkg",   # Custom package name (optional)
    "extractPassword": None,   # Archive extraction password
    "priority": "DEFAULT",     # HIGHEST, HIGHER, HIGH, DEFAULT, LOWER
    "downloadPassword": None,  # Download password
    "destinationFolder": None, # Custom download path
    "overwritePackagizerRules": False
}])
```

#### query_packages(params)
List packages in LinkCollector.

```python
packages = device.linkgrabber.query_packages([{
    "bytesTotal": True,
    "childCount": True,
    "comment": True,
    "enabled": True,
    "hosts": True,
    "maxResults": -1,    # -1 = all
    "priority": True,
    "saveTo": True,
    "startAt": 0,
    "status": True,
}])
# Returns: [{"uuid": 123, "name": "...", "bytesTotal": ..., ...}]
```

#### query_links(params)
List individual links with details.

```python
links = device.linkgrabber.query_links([{
    "bytesTotal": True,
    "comment": True,
    "status": True,
    "enabled": True,
    "maxResults": -1,
    "startAt": 0,
    "packageUUIDs": None,  # Filter by package UUIDs (list of int)
    "hosts": True,
    "url": True,
    "availability": True,  # ONLINE, OFFLINE, UNKNOWN
    "variantIcon": True,
    "variantName": True,
    "variantID": True,
    "variants": True,
    "priority": True,
}])
# Returns: [{"uuid": 456, "name": "file.mp4", "packageUUID": 123, ...}]
```

#### move_to_downloadlist(link_ids, package_ids)
Move items from LinkCollector to download queue.

```python
device.linkgrabber.move_to_downloadlist(
    [link_uuid1, link_uuid2],  # link IDs (list of int)
    [pkg_uuid1]                # package IDs (list of int)
)
```

#### move_to_new_package(link_ids, package_ids, new_pkg_name, download_path)
Move links to a new package (use this for "renaming" packages).

```python
device.linkgrabber.move_to_new_package(
    [link_uuid1, link_uuid2],  # link IDs to move
    [],                         # package IDs (usually empty)
    "New Package Name",         # new package name
    ""                          # download path (empty = default)
)
```

**GOTCHA:** This is the reliable way to rename packages. `rename_package` also exists but may not work in all versions.

#### rename_package(package_id, new_name)
Rename a package directly.

```python
device.linkgrabber.rename_package(package_uuid, "New Name")
```

#### rename_link(link_id, new_name)
Rename a link (file).

```python
device.linkgrabber.rename_link(link_uuid, "new_filename.mp4")
```


#### set_priority(priority, link_ids, package_ids)
Set priority of items.

```python
# priority: "HIGHEST", "HIGHER", "HIGH", "DEFAULT", "LOWER"
device.linkgrabber.set_priority("HIGH", [link_uuid], [])
```

#### set_enabled(enable, link_ids, package_ids)
Enable or disable items.

```python
device.linkgrabber.set_enabled(True, [link_uuid], [pkg_uuid])
```

#### get_variants(link_id_list)
Get quality variants for a link (e.g., YouTube video/audio options).

```python
variants = device.linkgrabber.get_variants([link_uuid])
# Returns: [{"id": "M4A_256", "name": "256kbit/s M4A-Audio"}, ...]
```

#### cleanup(action, mode, selection_type, link_ids, package_ids)
Clean up the LinkCollector.

```python
device.linkgrabber.cleanup(
    "DELETE_OFFLINE",              # Action: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED,
                                   #         DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE
    "REMOVE_LINKS_ONLY",          # Mode: REMOVE_LINKS_AND_DELETE_FILES,
                                   #       REMOVE_LINKS_AND_RECYCLE_FILES, REMOVE_LINKS_ONLY
    "ALL",                         # Selection: SELECTED, UNSELECTED, ALL, NONE
    [],                            # link_ids (optional filter)
    []                             # package_ids (optional filter)
)
```

#### clear_list()
Clear entire LinkCollector.

```python
device.linkgrabber.clear_list()
```

#### remove_links(link_ids, package_ids)
Remove specific items.

```python
device.linkgrabber.remove_links([link_uuid], [pkg_uuid])
```

#### add_container(type_, content)
Add DLC/RSDF/CCF container.

```python
device.linkgrabber.add_container("DLC", base64_content)
```

#### is_collecting()
Check if LinkCollector is processing.

```python
is_busy = device.linkgrabber.is_collecting()  # True/False
```

#### get_package_count()
Get total package count.

```python
count = device.linkgrabber.get_package_count()  # int
```

#### get_download_urls(link_ids, package_ids, url_display_type)
Get actual download URLs.

```python
urls = device.linkgrabber.get_download_urls([link_uuid], [], [])
```

---


### 2. Download Controller

Controls the download engine. Access: `device.downloadcontroller`

```python
device.downloadcontroller.start_downloads()       # Start/resume all
device.downloadcontroller.stop_downloads()        # Stop all
device.downloadcontroller.pause_downloads(True)   # Pause (True/False)
device.downloadcontroller.get_speed_in_bytes()    # Current speed (int, bytes/s)
device.downloadcontroller.get_current_state()     # "RUNNING", "STOPPED", "PAUSE", etc.
device.downloadcontroller.force_download(         # Force specific items
    [link_uuid], [pkg_uuid]
)
```

---

### 3. Downloads List

Active/completed downloads. Access: `device.downloads`

#### query_packages(params)
```python
packages = device.downloads.query_packages([{
    "bytesLoaded": True,
    "bytesTotal": True,
    "childCount": True,
    "comment": True,
    "enabled": True,
    "eta": True,
    "finished": True,
    "hosts": True,
    "maxResults": -1,
    "packageUUIDs": [],
    "priority": True,
    "running": True,
    "saveTo": True,
    "speed": True,
    "startAt": 0,
    "status": True,
}])
```

#### query_links(params)
```python
links = device.downloads.query_links([{
    "addedDate": True,
    "bytesLoaded": True,
    "bytesTotal": True,
    "comment": True,
    "enabled": True,
    "eta": True,
    "extractionStatus": True,
    "finished": True,
    "finishedDate": True,
    "host": True,
    "jobUUIDs": [],
    "maxResults": -1,
    "packageUUIDs": [],
    "password": True,
    "priority": True,
    "running": True,
    "skipped": True,
    "speed": True,
    "startAt": 0,
    "status": True,
    "url": True,
}])
```

#### Other downloads methods
```python
device.downloads.set_enabled(True, [link_ids], [pkg_ids])
device.downloads.force_download([link_ids], [pkg_ids])
device.downloads.set_dl_location("/path/to/dir", [pkg_ids])
device.downloads.remove_links([link_ids], [pkg_ids])
device.downloads.reset_links([link_ids], [pkg_ids])  # Re-download
device.downloads.move_to_new_package([link_ids], [], "New Name", "")
device.downloads.cleanup(action, mode, selection_type, [link_ids], [pkg_ids])
```

---


### 4. Captcha

Handle captchas programmatically. Access: `device.captcha`

```python
# List pending captchas
captchas = device.captcha.list()
# Returns: [{"id": 123, "type": "...", "hoster": "..."}]

# Get captcha image (base64)
image_b64 = device.captcha.get(captcha_id)

# Submit solution
device.captcha.solve(captcha_id, "solution_text")
```

**Captcha workflow:**
1. Poll `device.captcha.list()` periodically
2. When a captcha appears, get its image with `device.captcha.get(id)`
3. Solve it (manually, via OCR, or external service)
4. Submit with `device.captcha.solve(id, solution)`

---

### 5. Accounts (Premium Hosters)

Manage premium download accounts. Access: `device.accounts`

```python
# List all accounts
accounts = device.accounts.list_accounts([{
    "startAt": 0, "maxResults": -1,
    "userName": True, "validUntil": True,
    "trafficLeft": True, "trafficMax": True,
    "enabled": True, "valid": True, "error": False,
}])

# Add account
device.accounts.add_account("mega.nz", "user@email.com", "password")

# Enable/disable
device.accounts.enable_accounts([account_uuid1, account_uuid2])
device.accounts.disable_accounts([account_uuid1])

# Remove
device.accounts.remove_accounts([account_uuid1])

# Refresh/validate
device.accounts.refresh_accounts([account_uuid1])

# List supported hosters
hosters = device.accounts.list_premium_hoster()
hoster_urls = device.accounts.list_premium_hoster_urls()

# Basic auth (HTTP/FTP)
device.accounts.add_basic_auth("HTTP", "*.example.com", "user", "pass")
auths = device.accounts.list_basic_auth()
device.accounts.remove_basic_auths([auth_id])
device.accounts.update_basic_auth({
    "id": auth_id, "enabled": True,
    "hostmask": "*.example.com",
    "type": "HTTP", "username": "user", "password": "pass"
})

# Change credentials
device.accounts.set_user_name_and_password(account_uuid, "new_user", "new_pass")
```

---

### 6. System

System operations. Access: `device.system`

```python
device.system.restart_jd()          # Restart JDownloader
device.system.exit_jd()             # Close JDownloader
device.system.hibernate_os()        # Hibernate OS
device.system.shutdown_os(force)    # Shutdown (force=True/False)
device.system.standby_os()          # Standby
device.system.get_storage_info()    # Disk info
# Returns: [{"path": "/", "size": bytes, "free": bytes}]
```

---


### 7. Config (Advanced Settings)

Access: `device.config`

```python
# List/query all config entries
configs = device.config.query([{
    "configInterface": "",
    "defaultValues": True,
    "description": True,
    "enumInfo": True,
    "includeExtensions": True,
    "pattern": "speed",  # filter by keyword
    "values": True,
}])

# Get specific value
value = device.config.get(
    "org.jdownloader.settings.GeneralSettings",  # interface
    "null",                                       # storage
    "DefaultDownloadFolder"                       # key
)

# Set value
device.config.set(
    "org.jdownloader.settings.GeneralSettings",
    "null",
    "DefaultDownloadFolder",
    "/new/path"
)

# Get default value
default = device.config.getDefault(interface, storage, key)

# Reset to default
device.config.reset(interface, storage, key)

# List enum options
enums = device.config.listEnum("org.jdownloader.SomeEnumType")
```

**Common config interfaces:**
- `org.jdownloader.settings.GeneralSettings` - General settings
- `org.jdownloader.settings.GraphicalUserInterfaceSettings` - GUI
- `org.jdownloader.controlling.download.DownloadControllerConfig` - Download behavior

---

### 8. Extensions

Manage JDownloader plugins/extensions. Access: `device.extension`

```python
# List all extensions
extensions = device.extension.list([{
    "configInterface": True,
    "description": True,
    "enabled": True,
    "iconKey": True,
    "name": True,
    "pattern": "",
    "installed": True,
}])

# Install extension
device.extension.install("org.jdownloader.extensions.extraction.ExtractionExtension")

# Check status
device.extension.isInstalled(extension_id)  # bool
device.extension.isEnabled(extension_id)    # bool

# Enable/disable
device.extension.setEnabled(extension_id, True)
```

---

### 9. Dialogs

Handle JDownloader UI dialogs programmatically. Access: `device.dialog`

```python
# List open dialogs
dialog_ids = device.dialog.list()  # List of IDs

# Get dialog details
dialog = device.dialog.get(dialog_id, icon=True, properties=True)

# Get type info
type_info = device.dialog.getTypeInfo("DialogType")

# Answer a dialog
device.dialog.answer(dialog_id, {"response": "value"})
```

---

### 10. Toolbar

Speed limit control. Access: `device.toolbar`

```python
status = device.toolbar.get_status()
# Returns: {"limit": bool, "running": bool, "reconnect": bool, ...}

device.toolbar.enable_downloadSpeedLimit()
device.toolbar.disable_downloadSpeedLimit()
device.toolbar.status_downloadSpeedLimit()  # 1 if active, 0 if not
```

---

### 11. Update

```python
device.update.run_update_check()
device.update.is_update_available()   # bool
device.update.restart_and_update()    # restart + install update
device.update.update_available()      # combined: check + return bool
```

---

### 12. Reconnect

Trigger internet reconnect for new IP.

```python
device.reconnect.do_reconnect()
```

---

### 13. JD Info

```python
device.jd.get_core_revision()  # int (build number)
```

---


## Common Patterns & Gotchas

### Pattern: Add links and wait for them to be resolved

```python
import time

device.linkgrabber.add_links([{
    "autostart": False,
    "links": "https://youtube.com/watch?v=XXXXX",
    "packageName": "My Video",
}])

# Wait for links to be resolved
while device.linkgrabber.is_collecting():
    time.sleep(1)

# Now query the resolved links
links = device.linkgrabber.query_links([{"url": True, "availability": True}])
```

### Pattern: Rename packages by matching title

JDownloader auto-names packages from the page title. To rename:

```python
# Option A: rename_package (simpler, may not work in all cases)
device.linkgrabber.rename_package(package_uuid, "desired_name")

# Option B: move_to_new_package (reliable workaround)
# First get the link IDs in the package
links = device.linkgrabber.query_links([{"packageUUID": True}])
link_ids = [l["uuid"] for l in links if l["packageUUID"] == package_uuid]
device.linkgrabber.move_to_new_package(link_ids, [], "desired_name", "")
```

### Pattern: Download only specific variants (YouTube)

```python
# Get variants for a link
variants = device.linkgrabber.get_variants([link_uuid])
# Choose the one you want, then set it
# Note: set_variant is not fully implemented in myjdapi 1.1.10
```

### Gotcha: Rate Limiting

When adding many links (especially YouTube), add a delay between calls:
```python
import time
for url in urls:
    device.linkgrabber.add_links([{"links": url, "autostart": False}])
    time.sleep(2)  # 2 seconds between each
```

### Gotcha: UUIDs are integers

All UUIDs (package, link, account) are **integers**, not strings.

### Gotcha: Parameter order matters

The myjdapi library sends parameters positionally. Always follow the
exact parameter order shown in this documentation.

### Gotcha: query params are a list containing one dict

```python
# CORRECT:
device.linkgrabber.query_links([{"url": True, "bytesTotal": True}])

# WRONG:
device.linkgrabber.query_links({"url": True, "bytesTotal": True})
```

### Gotcha: add_links params are also a list containing one dict

```python
# CORRECT:
device.linkgrabber.add_links([{"links": "...", "autostart": False}])

# WRONG:
device.linkgrabber.add_links({"links": "...", "autostart": False})
```

---

## Captcha Auto-Solving Strategy

For automated captcha solving, the workflow is:

1. **Poll** `device.captcha.list()` in a loop
2. **Retrieve** image with `device.captcha.get(id)` (returns base64)
3. **Decode** the base64 image
4. **Solve** using one of:
   - OCR libraries (pytesseract, easyocr)
   - External services (2captcha, anticaptcha, nopecha)
   - ML models for specific captcha types
5. **Submit** solution with `device.captcha.solve(id, "answer")`

```python
import base64
import time

def auto_solve_captchas(device, solver_func, poll_interval=3):
    """
    Generic captcha auto-solver loop.
    solver_func receives raw image bytes, returns solution string.
    """
    while True:
        captchas = device.captcha.list()
        for captcha in captchas:
            cid = captcha["id"]
            image_b64 = device.captcha.get(cid)
            image_bytes = base64.b64decode(image_b64)
            solution = solver_func(image_bytes)
            if solution:
                device.captcha.solve(cid, solution)
                print(f"Solved captcha {cid}: {solution}")
        time.sleep(poll_interval)
```

---

## MCP Server Usage

This project includes a full MCP server. To use it:

### With Kiro / Claude Desktop

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "jdownloader": {
      "command": "python",
      "args": ["-m", "jdownloader_mcp.server"],
      "env": {
        "JD_EMAIL": "your_email",
        "JD_PASSWORD": "your_password",
        "JD_DEVICE_NAME": "optional_device_name"
      }
    }
  }
}
```

### Available MCP Tools

| Category | Tools |
|----------|-------|
| Connection | jd_connect, jd_disconnect, jd_reconnect, jd_list_devices, jd_switch_device |
| LinkCollector | jd_add_links, jd_linkgrabber_query_packages, jd_linkgrabber_query_links, jd_linkgrabber_move_to_downloadlist, jd_linkgrabber_move_to_new_package, jd_linkgrabber_rename_package, jd_linkgrabber_rename_link, jd_linkgrabber_set_priority, jd_linkgrabber_set_enabled, jd_linkgrabber_get_variants, jd_linkgrabber_cleanup, jd_linkgrabber_clear_list, jd_linkgrabber_remove_links, jd_linkgrabber_add_container, jd_linkgrabber_is_collecting, jd_linkgrabber_get_package_count, jd_linkgrabber_get_download_urls |
| Downloads | jd_start_downloads, jd_stop_downloads, jd_pause_downloads, jd_get_download_speed, jd_get_download_state, jd_force_download, jd_downloads_query_packages, jd_downloads_query_links, jd_downloads_set_enabled, jd_downloads_force_download, jd_downloads_set_location, jd_downloads_remove_links, jd_downloads_reset_links, jd_downloads_move_to_new_package, jd_downloads_cleanup |
| Captcha | jd_captcha_list, jd_captcha_get, jd_captcha_solve |
| Accounts | jd_accounts_list, jd_accounts_add, jd_accounts_remove, jd_accounts_enable, jd_accounts_disable, jd_accounts_refresh, jd_accounts_list_premium_hosters, jd_accounts_add_basic_auth, jd_accounts_list_basic_auth |
| System | jd_system_get_storage_info, jd_system_restart, jd_system_exit, jd_system_hibernate, jd_system_shutdown, jd_system_standby |
| Config | jd_config_list, jd_config_get, jd_config_set, jd_config_reset |
| Extensions | jd_extensions_list, jd_extensions_install, jd_extensions_set_enabled |
| Dialogs | jd_dialogs_list, jd_dialogs_get, jd_dialogs_answer |
| Toolbar | jd_toolbar_status, jd_speed_limit_enable, jd_speed_limit_disable |
| Update | jd_update_check, jd_update_restart |
| Misc | jd_reconnect, jd_get_version, jd_get_overview |
