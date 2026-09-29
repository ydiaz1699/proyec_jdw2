# JDownloader MCP Server + Skill

Control completo de JDownloader desde cualquier LLM usando el protocolo MCP
(Model Context Protocol) y/o como referencia (Skill) para generacion de codigo.

## Que incluye

```
proyec_jdw2/
├── src/jdownloader_mcp/          # MCP Server (100 tools)
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
│       │   ├── ml_solver.py      # CNN PyTorch propio
│       │   ├── nopecha_solver.py # NopeCHA API HTTP client
│       │   └── darknet_solver.py # cracker0dks/YOLO integration
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

## Uso como MCP Server

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

## Tools Disponibles (50+)

| Categoria | Tools |
|-----------|-------|
| Conexion | `jd_connect`, `jd_disconnect`, `jd_reconnect`, `jd_list_devices`, `jd_switch_device` |
| LinkCollector | `jd_add_links`, `jd_linkgrabber_query_packages`, `jd_linkgrabber_query_links`, `jd_linkgrabber_move_to_downloadlist`, `jd_linkgrabber_move_to_new_package`, `jd_linkgrabber_rename_package`, `jd_linkgrabber_rename_link`, `jd_linkgrabber_set_priority`, `jd_linkgrabber_set_enabled`, `jd_linkgrabber_get_variants`, `jd_linkgrabber_cleanup`, `jd_linkgrabber_clear_list`, `jd_linkgrabber_remove_links`, `jd_linkgrabber_add_container`, `jd_linkgrabber_is_collecting`, `jd_linkgrabber_get_package_count`, `jd_linkgrabber_get_download_urls` |
| Descargas | `jd_start_downloads`, `jd_stop_downloads`, `jd_pause_downloads`, `jd_get_download_speed`, `jd_get_download_state`, `jd_force_download`, `jd_downloads_query_packages`, `jd_downloads_query_links`, `jd_downloads_set_enabled`, `jd_downloads_force_download`, `jd_downloads_set_location`, `jd_downloads_remove_links`, `jd_downloads_reset_links`, `jd_downloads_move_to_new_package`, `jd_downloads_cleanup` |
| Captcha | `jd_captcha_list`, `jd_captcha_get`, `jd_captcha_solve` |
| Cuentas | `jd_accounts_list`, `jd_accounts_add`, `jd_accounts_remove`, `jd_accounts_enable`, `jd_accounts_disable`, `jd_accounts_refresh`, `jd_accounts_list_premium_hosters`, `jd_accounts_add_basic_auth`, `jd_accounts_list_basic_auth` |
| Sistema | `jd_system_get_storage_info`, `jd_system_restart`, `jd_system_exit`, `jd_system_hibernate`, `jd_system_shutdown`, `jd_system_standby` |
| Config | `jd_config_list`, `jd_config_get`, `jd_config_set`, `jd_config_reset` |
| Extensiones | `jd_extensions_list`, `jd_extensions_install`, `jd_extensions_set_enabled` |
| Dialogos | `jd_dialogs_list`, `jd_dialogs_get`, `jd_dialogs_answer` |
| Toolbar | `jd_toolbar_status`, `jd_speed_limit_enable`, `jd_speed_limit_disable` |
| Update | `jd_update_check`, `jd_update_restart` |
| Otros | `jd_reconnect`, `jd_get_version`, `jd_get_overview` |


## Captcha Auto-Solving (futuro)

El servidor incluye un módulo completo de auto-resolución de captchas
que funciona sin intervención humana:

### Arquitectura

```
JDownloader detecta captcha
        │
        ▼
MCP Server (jd_captcha_auto_solve_start)
        │
        ▼
┌─ AutoSolverDaemon (polling loop) ─┐
│                                    │
│  CaptchaRouter → detecta tipo      │
│       │                            │
│       ├─ DarkNet/YOLO (prioridad 10)
│       │   └─ cracker0dks integration
│       │                            │
│       ├─ ML CNN propio (prioridad 20)
│       │   └─ modelo entrenado .pth │
│       │                            │
│       ├─ OCR local (prioridad 30)  │
│       │   ├─ Tesseract             │
│       │   └─ EasyOCR               │
│       │                            │
│       └─ NopeCHA API (prioridad 50)│
│           └─ reCAPTCHA/hCaptcha/   │
│              Turnstile/FunCAPTCHA  │
│                                    │
│  device.captcha.solve(id, answer)  │
└────────────────────────────────────┘
```

### Componentes (auto-contenidos, sin dependencias externas):

| Solver | Tipo de captcha | Dependencia |
|--------|----------------|-------------|
| `DarkNetSolver` | Texto 6-digitos, geometrico (k2s, filejoker) | Node.js + darknet binary |
| `MLSolver` | Texto custom (entrenable) | PyTorch |
| `OCRSolver` | Texto/imagen generico | Tesseract y/o EasyOCR |
| `NopeCHASolver` | reCAPTCHA, hCaptcha, Turnstile, AWS WAF | requests (HTTP) |

### MCP Tools del auto-solver:

```
jd_captcha_auto_solve_start   # Iniciar daemon
jd_captcha_auto_solve_stop    # Detener daemon
jd_captcha_auto_solve_status  # Ver estadísticas
jd_captcha_auto_solve_reset   # Resetear stats/cache
```

### Instalación rápida:

```bash
# Mínimo (OCR + NopeCHA):
pip install Pillow pytesseract requests

# Con ML training:
pip install torch torchvision numpy

# Con EasyOCR (mejor para texto distorsionado):
pip install easyocr
```

### Integración cracker0dks/CaptchaSolver:

Para hosters como keep2share, fileboom, filejoker:
1. Descargar: https://github.com/cracker0dks/CaptchaSolver/releases
2. Extraer en tu carpeta de JDownloader
3. El solver lo detecta automáticamente en modo "integrated"

## Requisitos

- Python 3.10+
- JDownloader 2 corriendo con My.JDownloader activado
- Cuenta de My.JDownloader (gratis en https://my.jdownloader.org)
- Dispositivo vinculado y online

## Licencia

MIT
