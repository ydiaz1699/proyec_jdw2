---
name: jdownloader-usage
description: >-
  Usar el MCP de JDownloader para gestionar descargas por control remoto vía
  My.JDownloader. Activar cuando el usuario quiera añadir enlaces, iniciar o
  parar descargas, consultar el estado o velocidad, mover enlaces del
  LinkCollector a la lista de descargas, cambiar la carpeta de destino,
  gestionar cuentas premium, o resolver captchas. Requiere el servidor MCP
  "jdownloader" instalado (imagen ghcr.io/ydiaz1699/proyec_jdw2). NO cubre la
  instalación del MCP (ver INSTALL_PROMPT.md) ni descargas que no pasen por
  JDownloader.
license: MIT
metadata:
  author: ydiaz1699
  version: 1.0.0
  scope: usage
  auto_invoke:
    - jdownloader
    - descargar
    - jdownloader mcp
    - añadir enlace
    - linkgrabber
    - my.jdownloader
---

# Skill: uso del MCP de JDownloader

Guía para operar JDownloader a través del servidor MCP `jdownloader`. Todas las
herramientas empiezan por `jd_`. La conexión es **lazy**: si las variables de
entorno (`JD_EMAIL`, `JD_PASSWORD`, `JD_DEVICE_NAME`) están configuradas, la
primera tool que necesite el dispositivo conecta sola; no hace falta llamar a
`jd_connect` manualmente.

## Modelo mental de JDownloader

JDownloader tiene **dos listas**:

1. **LinkCollector (LinkGrabber):** zona de staging. Al añadir enlaces con
   `jd_add_links`, caen aquí primero. JDownloader analiza disponibilidad,
   tamaño, variantes, etc.
2. **Download List:** la cola real de descarga. Los enlaces se mueven aquí para
   empezar a bajar.

Flujo típico: `jd_add_links` → (revisar con `jd_query_links`) →
`jd_move_to_downloads` → `jd_start_downloads` → (seguir con
`jd_get_download_state` / `jd_get_speed`).

> Atajo: `jd_add_links(..., auto_start=True)` añade y arranca sin pasos
> intermedios.

## Comprobación inicial

Antes de operar, verifica la conexión:

- `jd_connection_status` → `{connected, email, device_name}`.
- `jd_list_devices` → lista de dispositivos vinculados.
- Si `connected` es `false` y hay credenciales, llama a cualquier tool o fuerza
  con `jd_connect`. Si falta el dispositivo, pide al usuario que verifique que
  JDownloader está abierto y online en My.JDownloader.

## Recetas por tarea

### Añadir enlaces y descargar

```
jd_add_links(
  links="https://ejemplo.com/f1\nhttps://ejemplo.com/f2",   # uno por línea o separados por espacio
  package_name="MiPaquete",        # opcional
  download_path="/ruta/destino",   # opcional
  auto_start=False,                # True = empieza a bajar ya
  extract_password=""              # opcional, para archivos protegidos
)
```

Si `auto_start=False`, luego:
```
jd_query_links()           # ver qué llegó al LinkCollector
jd_move_to_downloads(package_ids=[...])   # o link_ids=[...]
jd_start_downloads()
```

### Controlar la cola de descargas

- `jd_start_downloads` / `jd_stop_downloads` / `jd_pause_downloads(pause=True|False)`
- `jd_force_download(link_ids=[...])` — forzar aunque esté pausado/limitado.
- `jd_get_download_state` — estado global (running/paused/stopped).
- `jd_get_speed` — velocidad actual.
- `jd_query_packages_downloads` / `jd_query_downloads` — inspeccionar la cola.

### Carpeta de destino

- `jd_get_default_download_folder` / `jd_set_default_download_folder(path)` — global.
- `jd_set_download_directory(package_ids=[...], directory="/ruta")` — por paquete.

### Límite de velocidad

- `jd_set_speed_limit(bytes_per_second)` — p. ej. `1048576` = 1 MB/s; `0` = sin límite.

### Cuentas premium

- `jd_list_accounts`, `jd_add_account(hoster, username, password)`,
  `jd_enable_account(...)`, `jd_refresh_accounts`, `jd_list_premium_hosters`.

### Captchas

- `jd_list_captchas` → captchas pendientes.
- `jd_get_captcha(captcha_id)` → datos/imagen del captcha.
- `jd_solve_captcha(captcha_id, result)` → resolver a mano.
- `jd_auto_solve_captcha(captcha_id)` → intentar resolver con el auto-solver.
- Daemon en background: `jd_captcha_daemon_start` / `_status` / `_stop`,
  `jd_captcha_solvers_list`.

### Sistema y mantenimiento

- `jd_system_info`, `jd_get_storage_info`, `jd_get_session_info`.
- `jd_restart`, `jd_shutdown`, `jd_standby`, `jd_hibernate`.
- `jd_check_update`, `jd_run_update`, `jd_restart_and_update`.
- `jd_cleanup` / `jd_clear_linkgrabber` — limpiar listas.

## Buenas prácticas para el agente

- **Confirma antes de acciones destructivas o del sistema:** `jd_shutdown`,
  `jd_restart`, `jd_remove_links_*`, `jd_clear_linkgrabber`, `jd_cleanup`,
  `jd_hibernate`, `jd_standby`. Pregunta al usuario primero.
- **No inventes IDs.** Obtén `link_ids`/`package_ids` reales con
  `jd_query_links`, `jd_query_packages_linkgrabber` o `jd_query_packages_downloads`
  antes de mover/renombrar/borrar.
- **Normaliza enlaces:** acepta varios y pásalos uno por línea en `links`.
- **No reveles credenciales** (`JD_PASSWORD`, API keys) en respuestas ni logs.
- **Errores:** las tools devuelven texto JSON; si ves un error de conexión,
  comprueba `jd_connection_status` y que el dispositivo esté online.

## Referencia completa de categorías

| Categoría | Tools representativas |
|-----------|----------------------|
| Conexión | `jd_connect`, `jd_disconnect`, `jd_reconnect`, `jd_connection_status`, `jd_list_devices` |
| LinkCollector | `jd_add_links`, `jd_query_links`, `jd_query_packages_linkgrabber`, `jd_move_to_downloads`, `jd_move_packages`, `jd_rename_package_collector`, `jd_set_priority_collector`, `jd_add_container`, `jd_clear_linkgrabber`, `jd_remove_links_collector` |
| Descargas | `jd_start_downloads`, `jd_stop_downloads`, `jd_pause_downloads`, `jd_force_download`, `jd_get_download_state`, `jd_get_speed`, `jd_query_downloads`, `jd_query_packages_downloads`, `jd_set_download_directory`, `jd_remove_links_downloads`, `jd_reset_links` |
| Captcha | `jd_list_captchas`, `jd_get_captcha`, `jd_solve_captcha`, `jd_skip_captcha`, `jd_auto_solve_captcha`, `jd_captcha_daemon_start/stop/status`, `jd_captcha_solvers_list` |
| Cuentas | `jd_list_accounts`, `jd_add_account`, `jd_remove_account`, `jd_enable_account`, `jd_refresh_accounts`, `jd_list_premium_hosters`, `jd_toggle_premium` |
| Config | `jd_list_config_entries`, `jd_get_config_value`, `jd_set_config_value`, `jd_reset_config_value` |
| Sistema | `jd_system_info`, `jd_get_storage_info`, `jd_restart`, `jd_shutdown`, `jd_standby`, `jd_hibernate` |
| Update | `jd_check_update`, `jd_run_update`, `jd_restart_and_update` |
| Extensiones | `jd_list_extensions`, `jd_enable_extension` |
| Diálogos | `jd_list_dialogs`, `jd_get_dialog`, `jd_answer_dialog` |
| Eventos | `jd_subscribe_events`, `jd_poll_events` |
| Avanzado | `jd_call_action` (llamada cruda a la API), `jd_set_speed_limit`, `jd_toggle_reconnect` |
