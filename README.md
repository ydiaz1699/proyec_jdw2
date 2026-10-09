# JDownloader MCP Server + Skill

Control completo de JDownloader desde cualquier LLM usando el protocolo MCP
(Model Context Protocol) y/o como referencia (Skill) para generacion de codigo.

## Que incluye

```
proyec_jdw2/
├── src/jdownloader_mcp/          # MCP Server (76 tools)
│   ├── __init__.py
│   ├── server.py                 # Servidor MCP principal
│   └── captcha_solver/           # Módulo auto-solver
│       ├── __init__.py
│       ├── base.py               # Clases base (CaptchaType, BaseSolver)
│       ├── router.py             # Enrutador por tipo de captcha
│       ├── daemon.py             # Auto-solver background daemon
│       ├── preprocessing/
│       │   └── image_processor.py # Pipeline de procesamiento de imagen
│       ├── solvers/
│       │   ├── ocr_solver.py     # Tesseract + EasyOCR
│       │   ├── ml_solver.py      # CNN PyTorch (opt-in, requiere modelo .pth)
│       │   ├── nopecha_solver.py # NopeCHA API HTTP client
│       │   ├── twocaptcha_solver.py # 2Captcha API HTTP client
│       │   └── darknet_solver.py # YOLO/PyTorch (opt-in, requiere modelo .pt)
│       └── models/
│           └── cnn_model.py      # Arquitectura CNN para training
├── skill/
│   └── jdownloader.md            # Kiro Skill (referencia completa)
├── mcp_config.json               # Config para clientes MCP
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Instalacion Rapida

```bash
# 1. Clonar
git clone https://github.com/ydiaz1699/proyec_jdw2.git
cd proyec_jdw2

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales de My.JDownloader
```

## Uso con Docker (recomendado — solo configurar JSON)

> **Imagen pública verificada:** `ghcr.io/ydiaz1699/proyec_jdw2`. Compruébalo tú
> mismo sin autenticarte:
> ```bash
> docker logout ghcr.io
> docker pull ghcr.io/ydiaz1699/proyec_jdw2:latest   # descarga sin login = es pública
> ```
> ¿Quieres instalarlo con ayuda de un LLM? Usa el prompt de
> [`INSTALL_PROMPT.md`](INSTALL_PROMPT.md). Para operarlo, hay una skill de uso
> en [`skill/jdownloader-usage.md`](skill/jdownloader-usage.md).


La imagen se publica automáticamente en GitHub Container Registry (GHCR), así
que **no hace falta clonar el repo, ni instalar Python, ni `pip install`**. El
usuario final solo pega este JSON en su cliente MCP y pone sus credenciales:

```json
{
  "mcpServers": {
    "jdownloader": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "JD_EMAIL",
        "-e", "JD_PASSWORD",
        "-e", "JD_DEVICE_NAME",
        "ghcr.io/ydiaz1699/proyec_jdw2:latest"
      ],
      "env": {
        "JD_EMAIL": "tu_email@example.com",
        "JD_PASSWORD": "tu_password",
        "JD_DEVICE_NAME": "tu_dispositivo"
      }
    }
  }
}
```

Docker descarga la imagen la primera vez y la reutiliza después. Para captcha
remoto, añade `-e`, `"NOPECHA_API_KEY"` (y/o `TWOCAPTCHA_API_KEY`) al `args` y
la clave en `env`.

> La imagen se construye y publica sola vía GitHub Actions
> (`.github/workflows/docker-publish.yml`) en cada push a `main` y en cada tag
> `vX.Y.Z`. Un tag `v1.2.0` publica `:1.2.0`, `:1.2` y `:latest`.

### Construir la imagen localmente (opcional)

```bash
git clone https://github.com/ydiaz1699/proyec_jdw2.git
cd proyec_jdw2
docker build -t jdownloader-mcp .
# luego usa  "ghcr.io/ydiaz1699/proyec_jdw2:latest" -> "jdownloader-mcp" en el JSON
```

## Uso con uv / uvx (Windows u otro SO, sin Docker)

Ideal si **no tienes Docker** (p. ej. en Windows). `uvx` descarga el paquete en
un entorno aislado y efímero directamente desde este repo de GitHub y lo
ejecuta — **sin clonar, sin `pip install`, sin gestionar venvs**.

### Requisitos
- [`uv`](https://docs.astral.sh/uv/) instalado. En Windows (PowerShell):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- `git` instalado (lo necesita el `git+` de abajo).

### Config MCP
```json
{
  "mcpServers": {
    "jdownloader": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/ydiaz1699/proyec_jdw2.git",
        "jdownloader-mcp"
      ],
      "env": {
        "JD_EMAIL": "tu_email@example.com",
        "JD_PASSWORD": "tu_password",
        "JD_DEVICE_NAME": "tu_dispositivo"
      }
    }
  }
}
```

La primera vez `uvx` resuelve dependencias y construye el entorno (tarda unos
segundos); después queda cacheado. Para fijar una versión concreta en vez de la
rama por defecto, añade `@v1.1.0` al final de la URL del `--from`
(`...proyec_jdw2.git@v1.1.0`).

> No requiere PyPI: `uvx` instala desde el repo de GitHub. (Publicar en PyPI
> para poder usar el nombre corto `uvx jdownloader-mcp` queda como opción futura;
> PyPI oficial siempre es público.)

## Uso como MCP Server (Python, sin Docker)

### Con Kiro

Agregar en tu configuracion de MCP:


```json
{
  "mcpServers": {
    "jdownloader": {
      "command": "python",
      "args": ["-m", "jdownloader_mcp.server"],
      "cwd": "/ruta/a/proyec_jdw2/src",
      "env": {
        "JD_EMAIL": "tu_email",
        "JD_PASSWORD": "tu_password",
        "JD_DEVICE_NAME": "tu_dispositivo"
      }
    }
  }
}
```

> **Conexión lazy ("solo cuando se necesita").** Si defines `JD_EMAIL`,
> `JD_PASSWORD` y `JD_DEVICE_NAME` en el `env`, NO necesitas llamar `jd_connect`
> manualmente: la primera tool que requiera el dispositivo dispara la conexión
> sola leyendo esas variables. Si al arrancar My.JDownloader está lento o caído,
> el servidor arranca igual y reintenta la conexión en la primera tool. `jd_connect`
> sigue disponible para conectar a mano o cambiar de credenciales/dispositivo.

### Con Claude Desktop

Agregar en `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "jdownloader": {
      "command": "python",
      "args": ["-m", "jdownloader_mcp.server"],
      "cwd": "/ruta/a/proyec_jdw2/src",
      "env": {
        "JD_EMAIL": "tu_email",
        "JD_PASSWORD": "tu_password",
        "JD_DEVICE_NAME": "tu_dispositivo"
      }
    }
  }
}
```

### Ejecutar manualmente (para testing)

```bash
cd src
python -m jdownloader_mcp.server
```

## Uso como Kiro Skill

Copiar `skill/jdownloader.md` a:
- **Workspace:** `.kiro/skills/jdownloader.md`
- **Global:** `~/.kiro/skills/jdownloader.md`

Esto le da a Kiro (o cualquier LLM que lea el archivo) toda la referencia
necesaria para generar codigo que interactue con JDownloader sin necesidad
de leer la documentacion original de myjdapi.

## Tools Disponibles (76)

> Los nombres de abajo son los **reales** registrados por el servidor (verificados
> con `mcp.list_tools()` contra myjdapi 1.1.11). Todas empiezan por `jd_`.

| Categoria | Tools |
|-----------|-------|
| Conexion | `jd_connect`, `jd_disconnect`, `jd_reconnect`, `jd_connection_status`, `jd_list_devices` |
| LinkCollector | `jd_add_links`, `jd_query_links`, `jd_query_packages_linkgrabber`, `jd_move_to_downloads`, `jd_remove_links_collector`, `jd_clear_linkgrabber`, `jd_rename_link_collector`, `jd_rename_package_collector`, `jd_set_priority_collector`, `jd_add_container` |
| Descargas | `jd_start_downloads`, `jd_stop_downloads`, `jd_pause_downloads`, `jd_get_speed`, `jd_get_download_state`, `jd_force_download`, `jd_set_speed_limit`, `jd_query_downloads`, `jd_query_packages_downloads`, `jd_remove_links_downloads`, `jd_reset_links`, `jd_enable_links`, `jd_move_links`¹, `jd_move_packages`¹, `jd_rename_link_downloads`¹, `jd_rename_package_downloads`¹, `jd_set_priority_downloads`¹, `jd_set_download_directory`, `jd_cleanup` |
| Captcha | `jd_list_captchas`, `jd_get_captcha`, `jd_solve_captcha`, `jd_skip_captcha`, `jd_auto_solve_captcha`, `jd_captcha_daemon_start`, `jd_captcha_daemon_stop`, `jd_captcha_daemon_status`, `jd_captcha_solvers_list` |
| Cuentas | `jd_list_accounts`, `jd_add_account`, `jd_remove_account`, `jd_enable_account`, `jd_refresh_accounts`, `jd_list_premium_hosters` |
| Sistema | `jd_system_info`, `jd_get_storage_info`, `jd_restart`, `jd_exit`, `jd_shutdown_os`², `jd_hibernate`, `jd_standby` |
| Config | `jd_list_config_entries`, `jd_get_config_value`, `jd_set_config_value`, `jd_reset_config_value`, `jd_get_default_download_folder`, `jd_set_default_download_folder` |
| Extensiones | `jd_list_extensions`, `jd_enable_extension` |
| Dialogos | `jd_list_dialogs`, `jd_get_dialog`, `jd_answer_dialog` |
| Toolbar | `jd_toolbar_status`, `jd_speed_limit_toggle` |
| Update | `jd_check_update`, `jd_run_update_check`, `jd_restart_and_update` |
| Avanzado | `jd_call_action`, `jd_get_session_info`, `jd_poll_events`, `jd_subscribe_events` |

¹ **No probado contra un JD real.** myjdapi 1.1.11 no tiene estos métodos, así
que se implementan con la acción cruda `device.action("/downloadsV2/…")`. La ruta
de API está verificada, pero no se ha podido probar end-to-end en esta sesión.

² **`jd_shutdown_os` apaga la MÁQUINA (el SO), no sólo JDownloader.** Para cerrar
sólo la app usa `jd_exit`.


## Captcha Auto-Solving

El servidor incluye un módulo de auto-resolución de captchas con un router que
detecta el tipo y lo envía al solver adecuado, más un daemon que sondea
JDownloader en segundo plano.

### Estado real de cada solver

| Solver | Tipo de captcha | Dependencia | ¿Se registra por defecto? |
|--------|-----------------|-------------|----------------------------|
| `NopeCHASolver`   | reCAPTCHA v2/v3, hCaptcha, Turnstile, texto/imagen | `requests` (HTTP) | ✅ Sí, si `NOPECHA_API_KEY` está definido |
| `TwoCaptchaSolver`| reCAPTCHA v2/v3, hCaptcha, Turnstile, FunCaptcha, texto/imagen | `requests` (HTTP) | ✅ Sí, si `TWOCAPTCHA_API_KEY` está definido |
| `OCRSolver`       | Texto/imagen genérico | Tesseract y/o EasyOCR | ⚠️ Opt-in, **no cableado** |
| `MLSolver`        | Texto (CNN propio) | PyTorch + **modelo .pth entrenado (no incluido)** | ⚠️ Opt-in, **no cableado** |
| `DarkNetSolver`   | Geométrico/click (YOLO) | PyTorch + **modelo .pt (no incluido)** | ⚠️ Opt-in, **no cableado** |

> **Qué funciona hoy sin más:** sólo los solvers de API (NopeCHA / 2Captcha), y
> únicamente si defines su API key en el entorno. Sin ninguna key, el router
> queda vacío y las tools de auto-solve lo dicen con claridad en vez de fingir.
>
> **OCR/ML/YOLO son opt-in y no se registran automáticamente.** Requieren
> paquetes extra; además el `MLSolver` necesita un modelo CNN entrenado que este
> repo **no incluye** (no hay script de entrenamiento), y el `DarkNetSolver`
> necesita un modelo YOLO `.pt`. Los módulos de torch están protegidos: importar
> el paquete nunca arrastra torch ni falla si no está instalado.

### Cómo activar el auto-solver (API)

1. Define la API key en el entorno del MCP (`env` del JSON) — p. ej.
   `NOPECHA_API_KEY` y/o `TWOCAPTCHA_API_KEY`.
2. Para Docker, recuerda propagar la variable: añade
   `"-e", "NOPECHA_API_KEY"` al `args` y la clave en `env`.
3. Resolver un captcha concreto: `jd_auto_solve_captcha(captcha_id)`.
4. Modo desatendido: `jd_captcha_daemon_start` / `_status` / `_stop`.
   `jd_captcha_solvers_list` muestra los solvers registrados y sus stats.

### Dependencias opcionales (sólo si quieres OCR/ML)

```bash
pip install "jdownloader-mcp[ocr]"   # Tesseract/EasyOCR  (recuerda: apt install tesseract-ocr)
pip install "jdownloader-mcp[ml]"    # torch + numpy (para MLSolver/DarkNetSolver)
```

> El `MLSolver` seguirá deshabilitado hasta que le pases un `model_path` a un
> `.pth` entrenado. El entrenamiento del CNN queda fuera de este repo.

## Requisitos

- Python 3.10+
- JDownloader 2 corriendo con My.JDownloader activado
- Cuenta de My.JDownloader (gratis en https://my.jdownloader.org)
- Dispositivo vinculado y online

## Licencia

MIT
