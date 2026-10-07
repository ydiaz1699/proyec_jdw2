# Prompt de instalación — JDownloader MCP (para cualquier LLM)

Copia y pega el bloque de abajo en tu LLM/agente (Kiro, Claude, Cursor, etc.).
El asistente te guiará para dejar el MCP de JDownloader funcionando usando la
imagen Docker pública, **sin clonar el repo ni instalar Python**.

---

```text
Quiero instalar y configurar el servidor MCP "jdownloader" en mi cliente MCP
usando su imagen Docker pública de GitHub Container Registry. No quiero clonar
ningún repositorio ni instalar Python; solo quiero usar Docker y editar el JSON
de configuración de MCP.

Datos del servidor:
- Imagen pública: ghcr.io/ydiaz1699/proyec_jdw2:latest
- Transporte: stdio (el cliente lo lanza con `docker run -i --rm`).
- Credenciales que necesito proporcionar como variables de entorno:
  - JD_EMAIL         -> mi email de My.JDownloader (https://my.jdownloader.org)
  - JD_PASSWORD      -> mi contraseña de My.JDownloader
  - JD_DEVICE_NAME   -> el nombre del dispositivo JDownloader vinculado y online
- Opcionales (captcha remoto):
  - NOPECHA_API_KEY, TWOCAPTCHA_API_KEY
- Opcional: JD_LOG_LEVEL (DEBUG, INFO, WARNING, ERROR; por defecto INFO)

Por favor:
1) Verifica que tengo Docker instalado (`docker --version`). Si no, dime cómo
   instalarlo para mi sistema operativo.
2) Descarga la imagen para comprobar acceso: `docker pull ghcr.io/ydiaz1699/proyec_jdw2:latest`.
3) Dime la RUTA EXACTA del archivo de configuración MCP de MI cliente:
   - Kiro: el bloque mcpServers de la config de MCP de Kiro.
   - Claude Desktop (Mac): ~/Library/Application Support/Claude/claude_desktop_config.json
   - Claude Desktop (Windows): %APPDATA%\Claude\claude_desktop_config.json
   - Otro cliente: pregúntame cuál uso.
4) Añade/mergea esta entrada en la sección "mcpServers" (sin borrar lo que ya
   tenga). Sustituye los valores de env por los míos reales:

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
           "JD_EMAIL": "PON_AQUI_MI_EMAIL",
           "JD_PASSWORD": "PON_AQUI_MI_PASSWORD",
           "JD_DEVICE_NAME": "PON_AQUI_MI_DISPOSITIVO"
         }
       }
     }
   }

5) Recuérdame reiniciar el cliente MCP para que recargue la config.
6) Para probar, pídeme confirmación y luego usa la tool `jd_connection_status`
   (o `jd_list_devices`) para comprobar que el MCP conecta con mi JDownloader.
   La conexión es "lazy": no hace falta llamar a `jd_connect` a mano si las
   variables de entorno están puestas.

Antes de escribir en cualquier archivo, muéstrame el cambio exacto que vas a
hacer y espera mi confirmación. No expongas mis credenciales en logs.
```

---

## Alternativa sin Docker (Windows u otro SO) — con uv/uvx

Si NO tienes Docker (p. ej. en Windows), usa este prompt en su lugar. `uvx`
ejecuta el servidor desde el repo de GitHub sin clonar ni `pip install`.

```text
Quiero instalar y configurar el servidor MCP "jdownloader" en mi cliente MCP
usando uv/uvx (NO tengo Docker). No quiero clonar el repo ni gestionar venvs.

Datos del servidor:
- Se ejecuta con: uvx --from git+https://github.com/ydiaz1699/proyec_jdw2.git jdownloader-mcp
- Transporte: stdio.
- Credenciales (variables de entorno): JD_EMAIL, JD_PASSWORD, JD_DEVICE_NAME.
- Opcionales: NOPECHA_API_KEY, TWOCAPTCHA_API_KEY, JD_LOG_LEVEL.

Por favor:
1) Verifica que tengo `uv` instalado (`uv --version`). Si no, dime cómo
   instalarlo para mi SO. En Windows (PowerShell):
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   Verifica también que tengo `git` (lo necesita el `git+`).
2) Dime la ruta exacta del archivo de config MCP de mi cliente (Kiro, Claude
   Desktop, etc.); pregúntame cuál uso si no lo sabes.
3) Añade/mergea esta entrada en "mcpServers" (sin borrar lo que ya haya) y
   sustituye los valores de env por los míos reales:

   {
     "mcpServers": {
       "jdownloader": {
         "command": "uvx",
         "args": ["--from", "git+https://github.com/ydiaz1699/proyec_jdw2.git", "jdownloader-mcp"],
         "env": {
           "JD_EMAIL": "PON_AQUI_MI_EMAIL",
           "JD_PASSWORD": "PON_AQUI_MI_PASSWORD",
           "JD_DEVICE_NAME": "PON_AQUI_MI_DISPOSITIVO"
         }
       }
     }
   }

4) Recuérdame reiniciar el cliente MCP.
5) Para probar, usa la tool `jd_connection_status` (o `jd_list_devices`). La
   conexión es lazy: no hace falta `jd_connect` manual si el env está puesto.

Muéstrame el cambio exacto antes de escribir en cualquier archivo y espera mi
confirmación. No expongas mis credenciales en logs.
```

## Notas

- **Con Docker:** requisito único del usuario final = Docker instalado. Nada de Python/pip.
- **Con uv/uvx (sin Docker):** requisito = `uv` + `git` instalados. Recomendado en Windows.
- Para fijar una versión concreta en vez de `latest`, usa p. ej.
  `ghcr.io/ydiaz1699/proyec_jdw2:1.1.0`.
- Si tu LLM/cliente no ejecuta comandos, haz tú los pasos 1–2 y 5 a mano y deja
  que el asistente solo prepare el JSON del paso 4.
