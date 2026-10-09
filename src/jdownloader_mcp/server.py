"""JDownloader MCP Server"""
from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import myjdapi
from mcp.server.fastmcp import FastMCP

from jdownloader_mcp.captcha_solver import (
    AutoSolverDaemon,
    CaptchaRouter,
    CaptchaChallenge,
)

logger = logging.getLogger("jdownloader-mcp")

mcp = FastMCP(
    "JDownloader MCP Server",
    instructions="Full remote control of JDownloader via My.JDownloader API",
)


# ─── State ────────────────────────────────────────────────────────────────────

@dataclass
class JDState:
    """Holds the JDownloader connection state."""
    jd: Optional[myjdapi.Myjdapi] = None
    device: Optional[object] = None
    connected: bool = False
    email: str = ""
    password: str = ""          # guardada para reconexión lazy automática
    device_name: str = ""
    captcha_router: CaptchaRouter = field(default_factory=CaptchaRouter)
    captcha_daemon: Optional[AutoSolverDaemon] = None


state = JDState()


def _register_solvers() -> None:
    """Registra los solvers de captcha según las variables de entorno.

    Diseño honesto (ver README): sólo se registran los solvers que funcionan de
    verdad sin dependencias pesadas ni modelos entrenados, es decir los de API
    externa (2Captcha y NopeCHA), activados por su API key:

      - ``NOPECHA_API_KEY``   -> NopeCHASolver
      - ``TWOCAPTCHA_API_KEY`` -> TwoCaptchaSolver

    Los solvers OCR/ML/YOLO quedan como opt-in NO cableados aquí: requieren
    paquetes extra (torch/tesseract) y, en el caso del CNN, un modelo entrenado
    que este repo no incluye. Importarlos a nivel de módulo arrastraría torch,
    así que ni siquiera se importan si no hacen falta.

    Si no hay ninguna API key, el router queda vacío y las tools de auto-solve
    responden con un mensaje claro en vez de fingir que resuelven.
    """
    nopecha_key = os.environ.get("NOPECHA_API_KEY", "").strip()
    twocaptcha_key = os.environ.get("TWOCAPTCHA_API_KEY", "").strip()

    if nopecha_key:
        from jdownloader_mcp.captcha_solver.solvers.nopecha_solver import (
            NopeCHASolver,
        )
        solver = NopeCHASolver({"api_key": nopecha_key})
        if solver.enabled:
            # Prioridad 50: gratis/más barato primero.
            state.captcha_router.register_solver(solver, priority=50)

    if twocaptcha_key:
        from jdownloader_mcp.captcha_solver.solvers.twocaptcha_solver import (
            TwoCaptchaSolver,
        )
        solver = TwoCaptchaSolver({"api_key": twocaptcha_key})
        if solver.enabled:
            # Prioridad 60: servicio de pago, como respaldo.
            state.captcha_router.register_solver(solver, priority=60)

    if not state.captcha_router.solvers:
        logger.info(
            "Auto-solver sin solvers registrados. Define NOPECHA_API_KEY y/o "
            "TWOCAPTCHA_API_KEY para habilitar la resolución automática."
        )


def _has_env_credentials() -> bool:
    """True si hay credenciales disponibles (en el state o en el entorno)."""
    email = state.email or os.environ.get("JD_EMAIL", "")
    password = state.password or os.environ.get("JD_PASSWORD", "")
    device_name = state.device_name or os.environ.get("JD_DEVICE_NAME", "")
    return bool(email and password and device_name)


def _auto_connect_from_env() -> bool:
    """Intenta conectar leyendo JD_EMAIL / JD_PASSWORD / JD_DEVICE_NAME del entorno.

    Devuelve True si quedó conectado. Es el mecanismo que hace el MCP "lazy":
    no exige jd_connect() manual — la primera tool que necesite el device
    dispara la conexión sola si las credenciales están en el entorno.
    """
    email = state.email or os.environ.get("JD_EMAIL", "")
    password = state.password or os.environ.get("JD_PASSWORD", "")
    device_name = state.device_name or os.environ.get("JD_DEVICE_NAME", "")
    if not (email and password and device_name):
        return False
    jd_connect(email, password, device_name)
    return state.connected


def _require_device():
    """Devuelve el device conectado, conectando de forma lazy si hace falta.

    Comportamiento tipo nextdns ("solo cuando se necesita"):
      1. Si ya hay conexión → la devuelve.
      2. Si no → intenta auto-conectar desde el entorno (lazy).
      3. Distingue "sin credenciales" (hay que definir env o usar jd_connect)
         de "credenciales presentes pero el login falló" (revisar datos/red).
    """
    if state.connected and state.device is not None:
        return state.device
    if _auto_connect_from_env():
        return state.device
    if _has_env_credentials():
        raise RuntimeError(
            "No se pudo conectar a My.JDownloader con las credenciales del "
            "entorno. Revisa JD_EMAIL / JD_PASSWORD / JD_DEVICE_NAME y que el "
            "dispositivo esté online; reintenta con jd_reconnect()."
        )
    raise RuntimeError(
        "No conectado a JDownloader y sin credenciales en el entorno. "
        "Define JD_EMAIL / JD_PASSWORD / JD_DEVICE_NAME, o usa jd_connect()."
    )


def _ids(value) -> list:
    """Normaliza un parámetro de IDs a una lista.

    myjdapi espera listas (sus defaults son ``[]``); si una tool recibe ``None``
    y lo pasa tal cual, se rompe el default y la llamada puede fallar. Esta
    función convierte ``None`` → ``[]`` y envuelve un escalar suelto en lista.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]



# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION (5 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_connect(email: str, password: str, device_name: str) -> str:
    """Connect to My.JDownloader and select a device."""
    jd = myjdapi.Myjdapi()
    jd.set_app_key("jdownloader-mcp")
    try:
        jd.connect(email, password)
        jd.update_devices()
        device = jd.get_device(device_name)
        state.jd = jd
        state.device = device
        state.connected = True
        state.email = email
        state.password = password    # guardada para reconexión lazy
        state.device_name = device_name
        return f"Connected to device '{device_name}'"
    except Exception as e:
        state.connected = False
        return f"Connection failed: {e}"

@mcp.tool()
def jd_disconnect() -> str:
    """Disconnect from My.JDownloader."""
    if state.jd:
        try:
            state.jd.disconnect()
        except Exception:
            pass
    state.jd = None
    state.device = None
    state.connected = False
    return "Disconnected"

@mcp.tool()
def jd_reconnect() -> str:
    """Reconnect using stored credentials."""
    if not state.email:
        return "No previous connection. Use jd_connect() first."
    if state.jd:
        try:
            state.jd.reconnect()
            state.jd.update_devices()
            state.device = state.jd.get_device(state.device_name)
            state.connected = True
            return f"Reconnected to '{state.device_name}'"
        except Exception as e:
            state.connected = False
            return f"Reconnect failed: {e}"
    return "No JD instance. Use jd_connect()."

@mcp.tool()
def jd_list_devices() -> str:
    """List all available JDownloader devices.

    Dispara la conexión lazy: si no hay sesión aún pero hay credenciales en el
    entorno, conecta sola antes de listar (útil como primera tool de prueba).
    """
    if not state.jd:
        _auto_connect_from_env()
    if not state.jd:
        return ("Not connected. Define JD_EMAIL / JD_PASSWORD / JD_DEVICE_NAME "
                "o usa jd_connect() first.")
    try:
        state.jd.update_devices()
        return json.dumps(state.jd.list_devices(), indent=2, default=str)
    except Exception as e:
        return f"Error listing devices: {e}"

@mcp.tool()
def jd_connection_status() -> str:
    """Get current connection status.

    Intenta la conexión lazy desde el entorno si aún no está conectado, de forma
    que esta tool refleje el estado real tras un arranque sin warm-up.
    """
    if not state.connected:
        _auto_connect_from_env()
    return json.dumps({"connected": state.connected, "email": state.email, "device_name": state.device_name})



# ═══════════════════════════════════════════════════════════════════════════════
# LINKCOLLECTOR (10 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_add_links(links: str, package_name: str = "", download_path: str = "",
                 auto_start: bool = False, extract_password: str = "") -> str:
    """Add links to the LinkCollector."""
    device = _require_device()
    params = {"autostart": auto_start, "links": links}
    if package_name:
        params["packageName"] = package_name
    if download_path:
        params["destinationFolder"] = download_path
    if extract_password:
        params["extractPassword"] = extract_password
    try:
        result = device.linkgrabber.add_links([params])
        return json.dumps(result) if result else "Links added to LinkCollector"
    except Exception as e:
        return f"Error adding links: {e}"

@mcp.tool()
def jd_query_links(status: bool = True, availability: bool = True) -> str:
    """Query links currently in the LinkCollector."""
    device = _require_device()
    params = {"bytesTotal": True, "status": status, "availability": availability, "url": True, "enabled": True, "packageUUIDs": []}
    try:
        links = device.linkgrabber.query_links([params])
        return json.dumps(links, indent=2) if links else "No links in collector"
    except Exception as e:
        return f"Error querying links: {e}"

@mcp.tool()
def jd_query_packages_linkgrabber() -> str:
    """Query packages in the LinkCollector."""
    device = _require_device()
    params = {"bytesTotal": True, "childCount": True, "status": True, "saveTo": True, "availableOfflineCount": True, "availableOnlineCount": True}
    try:
        pkgs = device.linkgrabber.query_packages([params])
        return json.dumps(pkgs, indent=2) if pkgs else "No packages in collector"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_move_to_downloads(link_ids: list = None, package_ids: list = None) -> str:
    """Move links/packages from LinkCollector to download list."""
    device = _require_device()
    try:
        device.linkgrabber.move_to_downloadlist(_ids(link_ids), _ids(package_ids))
        return "Moved to download list"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_remove_links_collector(link_ids: list = None, package_ids: list = None) -> str:
    """Remove links/packages from LinkCollector."""
    device = _require_device()
    try:
        device.linkgrabber.remove_links(_ids(link_ids), _ids(package_ids))
        return "Removed from LinkCollector"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_clear_linkgrabber() -> str:
    """Clear all links from the LinkCollector."""
    device = _require_device()
    try:
        device.linkgrabber.clear_list()
        return "LinkCollector cleared"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_rename_link_collector(link_id: int, new_name: str) -> str:
    """Rename a link in the LinkCollector."""
    device = _require_device()
    try:
        device.linkgrabber.rename_link(link_id, new_name)
        return f"Link {link_id} renamed to '{new_name}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_rename_package_collector(package_id: int, new_name: str) -> str:
    """Rename a package in the LinkCollector."""
    device = _require_device()
    try:
        device.linkgrabber.rename_package(package_id, new_name)
        return f"Package {package_id} renamed to '{new_name}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_priority_collector(link_ids: list, package_ids: list, priority: str) -> str:
    """Set priority for links/packages in LinkCollector (HIGHEST, HIGH, DEFAULT, LOW, LOWEST)."""
    device = _require_device()
    try:
        device.linkgrabber.set_priority(priority, _ids(link_ids), _ids(package_ids))
        return f"Priority set to {priority}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_add_container(container_type: str, content: str) -> str:
    """Add DLC/CCF/RSDF container file content."""
    device = _require_device()
    try:
        result = device.linkgrabber.add_container(container_type, content)
        return json.dumps(result) if result else "Container added"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD CONTROLLER (7 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_start_downloads() -> str:
    """Start/resume the download controller."""
    device = _require_device()
    try:
        device.downloadcontroller.start_downloads()
        return "Downloads started"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_stop_downloads() -> str:
    """Stop/pause the download controller."""
    device = _require_device()
    try:
        device.downloadcontroller.stop_downloads()
        return "Downloads stopped"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_pause_downloads(pause: bool) -> str:
    """Pause or unpause downloads."""
    device = _require_device()
    try:
        device.downloadcontroller.pause_downloads(pause)
        return f"Downloads {'paused' if pause else 'unpaused'}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_speed() -> str:
    """Get current download speed."""
    device = _require_device()
    try:
        speed = device.downloadcontroller.get_speed_in_bytes()
        return f"{speed / (1024*1024):.2f} MB/s ({speed} bytes/s)"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_download_state() -> str:
    """Get current state of the download controller."""
    device = _require_device()
    try:
        return f"Download controller state: {device.downloadcontroller.get_current_state()}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_speed_limit(limit_bytes: int) -> str:
    """Set download speed limit in bytes/s (0 = unlimited).

    myjdapi 1.1.11 no tiene toolbar.set_download_speed_limit; el límite se
    aplica por configuración: se fija DownloadSpeedLimit y se activa/desactiva
    con DownloadSpeedLimitEnabled (0 bytes = sin límite => deshabilitado).
    """
    device = _require_device()
    iface = "org.jdownloader.settings.GeneralSettings"
    try:
        if limit_bytes and limit_bytes > 0:
            device.config.set(iface, "null", "DownloadSpeedLimit", limit_bytes)
            device.config.set(iface, "null", "DownloadSpeedLimitEnabled", True)
            return f"Speed limit set to {limit_bytes} bytes/s"
        else:
            device.config.set(iface, "null", "DownloadSpeedLimitEnabled", False)
            return "Speed limit disabled (unlimited)"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_force_download(link_ids: list = None, package_ids: list = None) -> str:
    """Force download of specific links/packages (bypass wait times)."""
    device = _require_device()
    try:
        device.downloadcontroller.force_download(_ids(link_ids), _ids(package_ids))
        return "Force download triggered"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# DOWNLOADS LIST (12 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_query_downloads(status: bool = True, speed: bool = True, eta: bool = True, finished: bool = True) -> str:
    """Query active/completed downloads."""
    device = _require_device()
    params = {"bytesLoaded": True, "bytesTotal": True, "speed": speed, "eta": eta, "status": status, "finished": finished, "enabled": True, "running": True, "url": True}
    try:
        links = device.downloads.query_links([params])
        return json.dumps(links, indent=2) if links else "No downloads"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_query_packages_downloads() -> str:
    """Query download packages in the download list."""
    device = _require_device()
    params = {"bytesLoaded": True, "bytesTotal": True, "childCount": True, "speed": True, "eta": True, "status": True, "finished": True, "enabled": True, "saveTo": True}
    try:
        pkgs = device.downloads.query_packages([params])
        return json.dumps(pkgs, indent=2) if pkgs else "No packages"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_remove_links_downloads(link_ids: list = None, package_ids: list = None) -> str:
    """Remove links/packages from the download list."""
    device = _require_device()
    try:
        device.downloads.remove_links(_ids(link_ids), _ids(package_ids))
        return "Removed from download list"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_reset_links(link_ids: list = None, package_ids: list = None) -> str:
    """Reset failed/completed links for retry."""
    device = _require_device()
    try:
        device.downloads.reset_links(_ids(link_ids), _ids(package_ids))
        return "Links reset"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_enable_links(enable: bool, link_ids: list = None, package_ids: list = None) -> str:
    """Enable or disable links/packages in download list."""
    device = _require_device()
    try:
        device.downloads.set_enabled(enable, _ids(link_ids), _ids(package_ids))
        return f"Links {'enabled' if enable else 'disabled'}"
    except Exception as e:
        return f"Error: {e}"

# NOTA: myjdapi 1.1.11 no expone estos métodos en la clase Downloads, así que
# se implementan con la acción cruda device.action() contra los endpoints
# /downloadsV2/* de la My.JDownloader API. Las rutas están verificadas contra la
# especificación de la API, pero NO se han podido probar contra un JDownloader
# real en esta sesión; por eso el docstring lo indica explícitamente.

@mcp.tool()
def jd_move_links(link_ids: list, after_link_id: int, dest_package_id: int) -> str:
    """Move links within the download list (vía /downloadsV2/moveLinks).

    Ruta de API verificada; no probada contra un JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/downloadsV2/moveLinks", [_ids(link_ids), after_link_id, dest_package_id])
        return "Links moved"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_move_packages(package_ids: list, after_package_id: int) -> str:
    """Move packages within the download list (vía /downloadsV2/movePackages).

    Ruta de API verificada; no probada contra un JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/downloadsV2/movePackages", [_ids(package_ids), after_package_id])
        return "Packages moved"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_rename_link_downloads(link_id: int, new_name: str) -> str:
    """Rename a link in the download list (vía /downloadsV2/renameLink).

    Ruta de API verificada; no probada contra un JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/downloadsV2/renameLink", [link_id, new_name])
        return f"Link {link_id} renamed to '{new_name}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_rename_package_downloads(package_id: int, new_name: str) -> str:
    """Rename a package in the download list (vía /downloadsV2/renamePackage).

    Ruta de API verificada; no probada contra un JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/downloadsV2/renamePackage", [package_id, new_name])
        return f"Package {package_id} renamed to '{new_name}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_priority_downloads(link_ids: list, package_ids: list, priority: str) -> str:
    """Set priority in download list (HIGHEST, HIGH, DEFAULT, LOW, LOWEST).

    Vía /downloadsV2/setPriority. Ruta de API verificada; no probada contra un
    JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/downloadsV2/setPriority", [priority, _ids(link_ids), _ids(package_ids)])
        return f"Priority set to {priority}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_download_directory(package_ids: list, directory: str) -> str:
    """Set download directory for packages."""
    device = _require_device()
    try:
        device.downloads.set_dl_location(directory, _ids(package_ids))
        return f"Directory set to '{directory}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_cleanup(action: str = "DELETE_FINISHED", mode: str = "REMOVE_LINKS_ONLY", selection: str = "ALL") -> str:
    """Cleanup download list. Actions: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED, DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE."""
    device = _require_device()
    try:
        device.downloads.cleanup(action, mode, selection)
        return f"Cleanup done: {action}"
    except Exception as e:
        return f"Error: {e}"





# ═══════════════════════════════════════════════════════════════════════════════
# CAPTCHA (9 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_list_captchas() -> str:
    """List pending captchas in JDownloader."""
    device = _require_device()
    try:
        captchas = device.captcha.list()
        return json.dumps(captchas, indent=2) if captchas else "No pending captchas"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_captcha(captcha_id: int) -> str:
    """Get captcha image as base64 string."""
    device = _require_device()
    try:
        image_b64 = device.captcha.get(captcha_id)
        if image_b64:
            return json.dumps({"captcha_id": captcha_id, "image_base64": image_b64})
        return f"No image for captcha {captcha_id}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_solve_captcha(captcha_id: int, solution: str) -> str:
    """Submit a captcha solution manually."""
    device = _require_device()
    try:
        device.captcha.solve(captcha_id, solution)
        return f"Captcha {captcha_id} solved with: '{solution}'"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_skip_captcha(captcha_id: int) -> str:
    """Skip a captcha challenge.

    myjdapi 1.1.11 no expone captcha.skip, así que se usa la acción cruda
    /captcha/skip de la My.JDownloader API. Ruta verificada contra la API; no
    probada contra un JD real en esta sesión.
    """
    device = _require_device()
    try:
        device.action("/captcha/skip", [captcha_id, "single"])
        return f"Captcha {captcha_id} skipped"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_auto_solve_captcha(captcha_id: int) -> str:
    """Attempt to auto-solve a captcha using the registered solvers."""
    device = _require_device()
    try:
        import base64
        image_b64 = device.captcha.get(captcha_id)
        if not image_b64:
            return f"No image for captcha {captcha_id}"
        image_data = base64.b64decode(image_b64)
        challenge = CaptchaChallenge(captcha_id=captcha_id, image_data=image_data, image_base64=image_b64)
        solution = state.captcha_router.solve(challenge)
        if solution.success and solution.solution:
            device.captcha.solve(captcha_id, solution.solution)
            return json.dumps({"success": True, "captcha_id": captcha_id, "solution": solution.solution,
                               "solver": solution.solver_name, "confidence": solution.confidence})
        return json.dumps({"success": False, "error": solution.error})
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_captcha_daemon_start() -> str:
    """Start the auto-solver daemon for automatic captcha resolution."""
    device = _require_device()
    if state.captcha_daemon and state.captcha_daemon.is_running:
        return "Daemon already running"
    if not state.captcha_router.solvers:
        return ("No hay solvers de captcha registrados. Define NOPECHA_API_KEY "
                "y/o TWOCAPTCHA_API_KEY e reinicia el servidor antes de arrancar "
                "el daemon.")
    # device_provider: el daemon relee state.device en cada iteración, así no
    # opera sobre un device obsoleto tras jd_reconnect().
    state.captcha_daemon = AutoSolverDaemon(
        device, state.captcha_router, device_provider=lambda: state.device
    )
    return state.captcha_daemon.start()

@mcp.tool()
def jd_captcha_daemon_stop() -> str:
    """Stop the auto-solver daemon."""
    if state.captcha_daemon:
        return state.captcha_daemon.stop()
    return "Daemon not running"

@mcp.tool()
def jd_captcha_daemon_status() -> str:
    """Get status of the captcha auto-solver daemon."""
    if state.captcha_daemon:
        return json.dumps(state.captcha_daemon.status(), indent=2, default=str)
    return json.dumps({"running": False})

@mcp.tool()
def jd_captcha_solvers_list() -> str:
    """List registered captcha solvers and their stats."""
    return json.dumps(state.captcha_router.solvers, indent=2)



# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTS (6 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_list_accounts() -> str:
    """List all hoster accounts configured in JDownloader."""
    device = _require_device()
    try:
        accounts = device.accounts.list_accounts()
        return json.dumps(accounts, indent=2) if accounts else "No accounts configured"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_add_account(hoster: str, username: str, password: str) -> str:
    """Add a premium hoster account."""
    device = _require_device()
    try:
        device.accounts.add_account(hoster, username, password)
        return f"Account added for {hoster}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_remove_account(account_ids: list) -> str:
    """Remove hoster accounts by their IDs."""
    device = _require_device()
    try:
        device.accounts.remove_accounts(account_ids)
        return f"Removed accounts: {account_ids}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_enable_account(account_id: int, enabled: bool) -> str:
    """Enable or disable a hoster account."""
    device = _require_device()
    try:
        if enabled:
            device.accounts.enable_accounts([account_id])
        else:
            device.accounts.disable_accounts([account_id])
        return f"Account {account_id} {'enabled' if enabled else 'disabled'}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_refresh_accounts() -> str:
    """Refresh/recheck all account statuses."""
    device = _require_device()
    try:
        device.accounts.refresh_accounts()
        return "Accounts refreshed"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_list_premium_hosters() -> str:
    """List premium hosters available with current accounts."""
    device = _require_device()
    try:
        hosters = device.accounts.list_premium_hoster_urls()
        return json.dumps(hosters, indent=2) if hosters else "No premium hosters"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM (6 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_system_info() -> str:
    """Get JDownloader storage/disk information.

    Nota: myjdapi 1.1.11 no expone un 'system infos' general; el dato de sistema
    disponible es el de almacenamiento (get_storage_info).
    """
    device = _require_device()
    try:
        return json.dumps(device.system.get_storage_info(), indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_restart() -> str:
    """Restart JDownloader."""
    device = _require_device()
    try:
        device.system.restart_jd()
        return "JDownloader restart triggered"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_exit() -> str:
    """Close the JDownloader application (does NOT power off the machine)."""
    device = _require_device()
    try:
        device.system.exit_jd()
        return "JDownloader exit triggered"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_shutdown_os(force: bool = False) -> str:
    """DANGER: power off the whole machine running JDownloader (the OS).

    This shuts down the host computer, not just JDownloader. To only close the
    JDownloader app, use jd_exit(). Confirm with the user before calling this.
    """
    device = _require_device()
    try:
        device.system.shutdown_os(force)
        return "OS shutdown triggered"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_hibernate() -> str:
    """Hibernate the system running JDownloader."""
    device = _require_device()
    try:
        device.system.hibernate_os()
        return "Hibernate triggered"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_standby() -> str:
    """Put system into standby mode."""
    device = _require_device()
    try:
        device.system.standby_os()
        return "Standby triggered"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_storage_info() -> str:
    """Get storage/disk space info."""
    device = _require_device()
    try:
        return json.dumps(device.system.get_storage_info(), indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG (6 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_list_config_entries(pattern: str = "") -> str:
    """List JDownloader configuration entries (optionally filter by pattern)."""
    device = _require_device()
    try:
        params = {"pattern": pattern} if pattern else {}
        entries = device.config.list(params)
        return json.dumps(entries, indent=2) if entries else "No config entries found"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_config_value(interface_name: str, key: str) -> str:
    """Get a specific config value."""
    device = _require_device()
    try:
        # myjdapi: get(interface_name, storage, key); 'null' = storage por defecto
        value = device.config.get(interface_name, "null", key)
        return json.dumps({"interface": interface_name, "key": key, "value": value}, default=str)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_config_value(interface_name: str, key: str, value: str) -> str:
    """Set a specific config value."""
    device = _require_device()
    try:
        # myjdapi: set(interface_name, storage, key, value)
        device.config.set(interface_name, "null", key, value)
        return f"Config set: {interface_name}.{key} = {value}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_reset_config_value(interface_name: str, key: str) -> str:
    """Reset a config value to its default."""
    device = _require_device()
    try:
        # myjdapi: reset(interfaceName, storage, key)
        device.config.reset(interface_name, "null", key)
        return f"Config reset: {interface_name}.{key}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_default_download_folder() -> str:
    """Get the default download folder."""
    device = _require_device()
    try:
        value = device.config.get(
            "org.jdownloader.settings.GeneralSettings", "null", "DefaultDownloadFolder"
        )
        return f"Default download folder: {value}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_set_default_download_folder(path: str) -> str:
    """Set the default download folder."""
    device = _require_device()
    try:
        device.config.set(
            "org.jdownloader.settings.GeneralSettings", "null", "DefaultDownloadFolder", path
        )
        return f"Default download folder set to: {path}"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# EXTENSIONS (2 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_list_extensions() -> str:
    """List installed JDownloader extensions and their status."""
    device = _require_device()
    try:
        params = {"installed": True, "enabled": True, "name": True}
        exts = device.extensions.list(params)
        return json.dumps(exts, indent=2) if exts else "No extensions"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_enable_extension(class_name: str, enabled: bool) -> str:
    """Enable or disable an extension by its class name."""
    device = _require_device()
    try:
        device.extensions.setEnabled(class_name, enabled)
        return f"Extension {class_name} {'enabled' if enabled else 'disabled'}"
    except Exception as e:
        return f"Error: {e}"





# ═══════════════════════════════════════════════════════════════════════════════
# DIALOGS (3 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_list_dialogs() -> str:
    """List pending dialogs in JDownloader."""
    device = _require_device()
    try:
        dialogs = device.dialogs.list()
        return json.dumps(dialogs, indent=2) if dialogs else "No pending dialogs"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_dialog(dialog_id: int) -> str:
    """Get details about a specific dialog."""
    device = _require_device()
    try:
        return json.dumps(device.dialogs.get(dialog_id), indent=2)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_answer_dialog(dialog_id: int, response: dict) -> str:
    """Answer/dismiss a pending dialog."""
    device = _require_device()
    try:
        device.dialogs.answer(dialog_id, response)
        return f"Dialog {dialog_id} answered"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# TOOLBAR (5 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_toolbar_status() -> str:
    """Get current toolbar status (speed limit, clipboard, reconnect, premium, etc.)."""
    device = _require_device()
    try:
        return json.dumps(device.toolbar.get_status(), indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_speed_limit_toggle(enabled: bool) -> str:
    """Enable or disable the download speed limit (toolbar toggle).

    Usa los métodos reales de myjdapi (enable/disable_downloadSpeedLimit). Para
    fijar el VALOR del límite en bytes/s usa jd_set_speed_limit.
    """
    device = _require_device()
    try:
        if enabled:
            device.toolbar.enable_downloadSpeedLimit()
        else:
            device.toolbar.disable_downloadSpeedLimit()
        return f"Speed limit {'enabled' if enabled else 'disabled'}"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# UPDATE (3 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_check_update() -> str:
    """Check if a JDownloader update is available."""
    device = _require_device()
    try:
        return f"Update available: {device.update.is_update_available()}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_run_update_check() -> str:
    """Trigger an update check in JDownloader.

    myjdapi 1.1.11 expone run_update_check (no run_update). Para instalar y
    reiniciar con la actualización, usa jd_restart_and_update.
    """
    device = _require_device()
    try:
        device.update.run_update_check()
        return "Update check triggered."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_restart_and_update() -> str:
    """Restart JDownloader and install available updates."""
    device = _require_device()
    try:
        device.update.restart_and_update()
        return "Restart + update triggered"
    except Exception as e:
        return f"Error: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# RAW / EXTENDED API (4 tools)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def jd_call_action(action: str, params: list = None) -> str:
    """Call any JDownloader API action directly. Use /action/endpoint format."""
    device = _require_device()
    try:
        result = device.action(action, params)
        return json.dumps(result, indent=2, default=str) if result else "Action executed (no return)"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_get_session_info() -> str:
    """Get session and device information."""
    return json.dumps({
        "connected": state.connected, "email": state.email, "device_name": state.device_name,
        "captcha_daemon_running": state.captcha_daemon.is_running if state.captcha_daemon else False,
        "registered_solvers": len(state.captcha_router.solvers),
    }, indent=2)

@mcp.tool()
def jd_poll_events(subscription_id: str = None) -> str:
    """Poll for events from a subscription."""
    device = _require_device()
    try:
        if subscription_id:
            events = device.events.poll(subscription_id)
        else:
            events = device.events.list_publisher()
        return json.dumps(events, indent=2) if events else "No events"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def jd_subscribe_events(subscriptions: list, exclusions: list = None) -> str:
    """Subscribe to JDownloader events."""
    device = _require_device()
    try:
        result = device.events.add_subscription(subscriptions, exclusions or [])
        return json.dumps(result, indent=2) if result else "Subscribed"
    except Exception as e:
        return f"Error: {e}"





# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Main entry point for the JDownloader MCP server."""
    log_level = os.environ.get("JD_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Registrar los solvers de captcha según las API keys del entorno. Si no hay
    # ninguna, el auto-solver queda vacío y lo dice con claridad.
    _register_solvers()

    # Warm-up opcional: si hay credenciales en el entorno, intenta conectar al
    # arrancar para fallar rápido y avisar en logs. Si MyJDownloader está lento o
    # caído aquí, NO es fatal: la conexión lazy en _require_device() reintenta en
    # la primera tool. El servidor arranca igual.
    if os.environ.get("JD_EMAIL") and os.environ.get("JD_PASSWORD") \
            and os.environ.get("JD_DEVICE_NAME"):
        logger.info("Warm-up: intentando conectar desde el entorno...")
        if _auto_connect_from_env():
            logger.info(f"Conectado a '{state.device_name}'.")
        else:
            logger.warning(
                "Warm-up sin conexión; se reintentará de forma lazy en la "
                "primera tool que la necesite."
            )

    mcp.run()


if __name__ == "__main__":
    main()
