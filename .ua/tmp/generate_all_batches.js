const fs = require('fs');
const path = require('path');

const projectRoot = 'C:/Users/Alex/Desktop/1-Github/proyec_jdw2';
const uaDir = path.join(projectRoot, '.ua');
const interDir = path.join(uaDir, 'intermediate');

// ==========================================
// BATCH 1: CAPTCHA SOLVER SUBSYSTEM & SERVER
// ==========================================
const batch1 = {
  nodes: [
    {
      id: "file:src/jdownloader_mcp/server.py",
      type: "file",
      name: "server.py",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Servidor principal FastMCP que expone 79 herramientas de control remoto para JDownloader, resolución de captchas e integración inteligente con YouTube.",
      tags: ["entry-point", "api-handler", "mcp-server", "fastmcp"],
      complexity: "complex"
    },
    {
      id: "class:src/jdownloader_mcp/server.py:JDState",
      type: "class",
      name: "JDState",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Mantiene el estado global de conexión a My.JDownloader, dispositivo activo, credenciales y referencias al enrutador y daemon de captchas.",
      tags: ["state-management", "singleton", "data-model"],
      complexity: "simple",
      lineRange: [29, 41]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_connect",
      type: "function",
      name: "jd_connect",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Autentica con la API My.JDownloader y selecciona o valida el dispositivo objetivo.",
      tags: ["authentication", "connection", "api-handler"],
      complexity: "moderate",
      lineRange: [95, 125]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_add_links",
      type: "function",
      name: "jd_add_links",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Agrega enlaces o paquetes al LinkGrabber de JDownloader con configuración de autoinicio y destino.",
      tags: ["linkgrabber", "download", "api-handler"],
      complexity: "moderate",
      lineRange: [180, 220]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_solve_captcha",
      type: "function",
      name: "jd_solve_captcha",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Envía un reto de captcha al solver configurado y envía la respuesta a JDownloader.",
      tags: ["captcha", "solver", "automation"],
      complexity: "moderate",
      lineRange: [650, 700]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_add_youtube_smart",
      type: "function",
      name: "jd_add_youtube_smart",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Herramienta MCP inteligente que agrega un video de YouTube, detecta su idioma y filtra variantes conservando video, subtítulos SRT y miniatura.",
      tags: ["youtube", "filter", "smart-download"],
      complexity: "moderate",
      lineRange: [1113, 1135]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_filter_youtube_collector",
      type: "function",
      name: "jd_filter_youtube_collector",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Filtra los elementos de YouTube existentes en el LinkCollector de JDownloader purgando pistas de audio sueltas no deseadas.",
      tags: ["youtube", "link-filter", "cleanup"],
      complexity: "moderate",
      lineRange: [1138, 1162]
    },
    {
      id: "function:src/jdownloader_mcp/server.py:jd_sync_youtube_channel",
      type: "function",
      name: "jd_sync_youtube_channel",
      filePath: "src/jdownloader_mcp/server.py",
      summary: "Sincroniza un canal de YouTube con JDownloader: detecta videos nuevos mediante diff incremental y los envía filtrados al LinkGrabber.",
      tags: ["youtube", "sync", "incremental"],
      complexity: "moderate",
      lineRange: [1165, 1184]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/captcha_solver/__init__.py",
      summary: "Punto de entrada del paquete captcha_solver; reexporta las abstracciones base, solvers, router y daemon.",
      tags: ["barrel", "exports", "package-root"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/base.py",
      type: "file",
      name: "base.py",
      filePath: "src/jdownloader_mcp/captcha_solver/base.py",
      summary: "Define las interfaces abstractas y modelos de datos tipados para la resolución de captchas (desafíos, soluciones y tipos).",
      tags: ["interfaces", "data-model", "captcha"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver",
      type: "class",
      name: "BaseSolver",
      filePath: "src/jdownloader_mcp/captcha_solver/base.py",
      summary: "Clase abstracta base para la implementación de resolutores de captchas de cualquier proveedor.",
      tags: ["abstract-class", "plugin-pattern", "captcha"],
      complexity: "simple",
      lineRange: [60, 92]
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/base.py:CaptchaChallenge",
      type: "class",
      name: "CaptchaChallenge",
      filePath: "src/jdownloader_mcp/captcha_solver/base.py",
      summary: "Dataclass que modela un reto de captcha con id, tipo, datos en base64 o texto y contexto adicional.",
      tags: ["data-model", "captcha", "dataclass"],
      complexity: "simple",
      lineRange: [25, 45]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/router.py",
      type: "file",
      name: "router.py",
      filePath: "src/jdownloader_mcp/captcha_solver/router.py",
      summary: "Enrutador de captchas que asigna cada desafío al solver más adecuado según el tipo de captcha y disponibilidad.",
      tags: ["router", "strategy-pattern", "captcha"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/router.py:CaptchaRouter",
      type: "class",
      name: "CaptchaRouter",
      filePath: "src/jdownloader_mcp/captcha_solver/router.py",
      summary: "Gestiona el registro de solvers y la lógica de enrutamiento y reintentos ante fallas de resolución.",
      tags: ["dispatcher", "registry", "failover"],
      complexity: "moderate",
      lineRange: [20, 130]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/daemon.py",
      type: "file",
      name: "daemon.py",
      filePath: "src/jdownloader_mcp/captcha_solver/daemon.py",
      summary: "Daemon en segundo plano que monitorea activamente la cola de captchas en JDownloader y los resuelve automáticamente.",
      tags: ["daemon", "background-task", "polling"],
      complexity: "complex"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/daemon.py:AutoSolverDaemon",
      type: "class",
      name: "AutoSolverDaemon",
      filePath: "src/jdownloader_mcp/captcha_solver/daemon.py",
      summary: "Hilo de ejecución en segundo plano para auto-resolución continua con gestión de concurrencia y límites de reintento.",
      tags: ["thread", "automation", "worker"],
      complexity: "complex",
      lineRange: [25, 250]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py",
      type: "file",
      name: "darknet_solver.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py",
      summary: "Solver local de captchas basado en redes neuronales convolucionales DarkNet / YOLO.",
      tags: ["solver", "computer-vision", "neural-network"],
      complexity: "complex"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py:DarkNetSolver",
      type: "class",
      name: "DarkNetSolver",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py",
      summary: "Implementación de BaseSolver para inferencia sobre modelos DarkNet.",
      tags: ["neural-network", "inference", "solver"],
      complexity: "complex",
      lineRange: [30, 340]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py",
      type: "file",
      name: "ml_solver.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py",
      summary: "Solver genérico de Machine Learning para clasificación de imágenes de captchas locales.",
      tags: ["solver", "machine-learning", "classification"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py:MLSolver",
      type: "class",
      name: "MLSolver",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py",
      summary: "Implementa inferencia con modelos locales entrenados para captchas de caracteres.",
      tags: ["ml", "solver", "vision"],
      complexity: "moderate",
      lineRange: [25, 215]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py",
      type: "file",
      name: "nopecha_solver.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py",
      summary: "Integración con la API externa de NopeCHA para resolver captchas complejos en la nube.",
      tags: ["api-client", "external-service", "nopecha"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py:NopeCHASolver",
      type: "class",
      name: "NopeCHASolver",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py",
      summary: "Cliente REST para el servicio NopeCHA con soporte para hCaptcha, reCAPTCHA y Turnstile.",
      tags: ["http-client", "nopecha", "solver"],
      complexity: "moderate",
      lineRange: [20, 240]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py",
      type: "file",
      name: "ocr_solver.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py",
      summary: "Solver local de OCR basado en Tesseract para captchas simples basados en texto.",
      tags: ["ocr", "tesseract", "text-extraction"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py:OCRSolver",
      type: "class",
      name: "OCRSolver",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py",
      summary: "Aplica preprocesamiento de imagen y Tesseract OCR para resolver retos de texto.",
      tags: ["ocr", "image-processing", "solver"],
      complexity: "moderate",
      lineRange: [20, 225]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py",
      type: "file",
      name: "twocaptcha_solver.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py",
      summary: "Integración oficial con la API 2Captcha para resolución comercial de alta fiabilidad.",
      tags: ["api-client", "2captcha", "external-service"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py:TwoCaptchaSolver",
      type: "class",
      name: "TwoCaptchaSolver",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py",
      summary: "Gestiona envíos y consultas de resultados ante la plataforma 2Captcha.",
      tags: ["2captcha", "http-client", "solver"],
      complexity: "moderate",
      lineRange: [20, 195]
    }
  ],
  edges: [
    { source: "file:src/jdownloader_mcp/server.py", target: "class:src/jdownloader_mcp/server.py:JDState", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_connect", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_add_links", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_solve_captcha", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_add_youtube_smart", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_filter_youtube_collector", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "function:src/jdownloader_mcp/server.py:jd_sync_youtube_channel", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/server.py", target: "file:src/jdownloader_mcp/captcha_solver/__init__.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/__init__.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/__init__.py", target: "file:src/jdownloader_mcp/captcha_solver/router.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/__init__.py", target: "file:src/jdownloader_mcp/captcha_solver/daemon.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/base.py", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/base.py", target: "class:src/jdownloader_mcp/captcha_solver/base.py:CaptchaChallenge", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/router.py", target: "class:src/jdownloader_mcp/captcha_solver/router.py:CaptchaRouter", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/router.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/daemon.py", target: "class:src/jdownloader_mcp/captcha_solver/daemon.py:AutoSolverDaemon", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/daemon.py", target: "file:src/jdownloader_mcp/captcha_solver/router.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/daemon.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py", target: "class:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py:DarkNetSolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "class:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py:DarkNetSolver", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "inherits", weight: 0.9 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py", target: "class:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py:MLSolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "class:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py:MLSolver", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "inherits", weight: 0.9 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py", target: "class:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py:NopeCHASolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "class:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py:NopeCHASolver", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "inherits", weight: 0.9 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py", target: "class:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py:OCRSolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "class:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py:OCRSolver", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "inherits", weight: 0.9 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py", target: "class:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py:TwoCaptchaSolver", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/base.py", type: "imports", weight: 0.7 },
    { source: "class:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py:TwoCaptchaSolver", target: "class:src/jdownloader_mcp/captcha_solver/base.py:BaseSolver", type: "inherits", weight: 0.9 }
  ]
};

// ==========================================
// BATCH 2: YOUTUBE ENGINE & EXTRACTION PIPELINE
// ==========================================
const batch2 = {
  nodes: [
    {
      id: "file:src/jdownloader_mcp/youtube/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/youtube/__init__.py",
      summary: "Punto de entrada del paquete youtube; exporta funciones clave del pipeline, enrutador de claves y detección de idioma.",
      tags: ["barrel", "exports", "youtube"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/youtube/api.py",
      type: "file",
      name: "api.py",
      filePath: "src/jdownloader_mcp/youtube/api.py",
      summary: "Cliente oficial de YouTube Data API v3 con soporte para paginación, retries con backoff y extracción de playlists UULF.",
      tags: ["api-client", "youtube-api", "networking"],
      complexity: "complex"
    },
    {
      id: "function:src/jdownloader_mcp/youtube/api.py:get_channel_id",
      type: "function",
      name: "get_channel_id",
      filePath: "src/jdownloader_mcp/youtube/api.py",
      summary: "Resuelve el Channel ID de YouTube a partir de un handle (@canal), id directo o URL.",
      tags: ["resolver", "youtube-channel", "utility"],
      complexity: "moderate",
      lineRange: [40, 75]
    },
    {
      id: "function:src/jdownloader_mcp/youtube/api.py:get_uploads_playlist_id",
      type: "function",
      name: "get_uploads_playlist_id",
      filePath: "src/jdownloader_mcp/youtube/api.py",
      summary: "Obtiene la playlist de videos largos (UULF...) o subidas directas del canal excluyendo Shorts nativamente.",
      tags: ["playlist", "filter-shorts", "youtube-api"],
      complexity: "simple",
      lineRange: [78, 98]
    },
    {
      id: "function:src/jdownloader_mcp/youtube/api.py:get_playlist_items",
      type: "function",
      name: "get_playlist_items",
      filePath: "src/jdownloader_mcp/youtube/api.py",
      summary: "Descarga todos los items de una playlist mediante paginación exhaustiva con reintentos automáticos.",
      tags: ["pagination", "batch-fetch", "youtube-api"],
      complexity: "moderate",
      lineRange: [100, 160]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/key_router.py",
      type: "file",
      name: "key_router.py",
      filePath: "src/jdownloader_mcp/youtube/key_router.py",
      summary: "Gestor multi-llave para YouTube Data API v3 con rotación automática por cuota agotada y reinicio a medianoche del Pacífico.",
      tags: ["key-rotation", "quota-management", "rate-limiting"],
      complexity: "complex"
    },
    {
      id: "class:src/jdownloader_mcp/youtube/key_router.py:KeyRouter",
      type: "class",
      name: "KeyRouter",
      filePath: "src/jdownloader_mcp/youtube/key_router.py",
      summary: "Controlador de rotación de claves API que registra cuota por slot y conmuta sin interrupción de servicio.",
      tags: ["router", "failover", "api-keys"],
      complexity: "complex",
      lineRange: [45, 190]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/quota.py",
      type: "file",
      name: "quota.py",
      filePath: "src/jdownloader_mcp/youtube/quota.py",
      summary: "Persistencia de cuota diaria consumida por API key en archivo local con soporte para zona horaria de California.",
      tags: ["persistence", "quota", "cache"],
      complexity: "moderate"
    },
    {
      id: "function:src/jdownloader_mcp/youtube/quota.py:registrar_uso",
      type: "function",
      name: "registrar_uso",
      filePath: "src/jdownloader_mcp/youtube/quota.py",
      summary: "Registra unidades de cuota consumidas por llamada a la API en el almacenamiento local.",
      tags: ["accounting", "quota", "metrics"],
      complexity: "simple",
      lineRange: [40, 58]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/language.py",
      type: "file",
      name: "language.py",
      filePath: "src/jdownloader_mcp/youtube/language.py",
      summary: "Motor heurístico de detección de idioma que combina metadatos oficiales, defaultAudioLanguage y frecuencias léxicas.",
      tags: ["nlp", "language-detection", "heuristics"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/youtube/language.py:LanguageDetectionResult",
      type: "class",
      name: "LanguageDetectionResult",
      filePath: "src/jdownloader_mcp/youtube/language.py",
      summary: "Estructura de datos con el idioma detectado, nivel de confianza, método utilizado y banderas de validación.",
      tags: ["data-model", "dataclass", "nlp"],
      complexity: "simple",
      lineRange: [15, 30]
    },
    {
      id: "function:src/jdownloader_mcp/youtube/language.py:detect_video_language",
      type: "function",
      name: "detect_video_language",
      filePath: "src/jdownloader_mcp/youtube/language.py",
      summary: "Determina si un video está en español u otro idioma utilizando análisis multi-fuente de alta precisión.",
      tags: ["classification", "language", "nlp"],
      complexity: "moderate",
      lineRange: [90, 150]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/filter.py",
      type: "file",
      name: "filter.py",
      filePath: "src/jdownloader_mcp/youtube/filter.py",
      summary: "Filtro inteligente de variantes de JDownloader: conserva video MP4/MKV, miniaturas JPG/PNG, descripción y subtítulos SRT en cualquier idioma.",
      tags: ["filter", "cleanup", "subtitles-preserve"],
      complexity: "moderate"
    },
    {
      id: "function:src/jdownloader_mcp/youtube/filter.py:classify_youtube_link",
      type: "function",
      name: "classify_youtube_link",
      filePath: "src/jdownloader_mcp/youtube/filter.py",
      summary: "Clasifica enlaces del colector en categorías (video, audio, subtítulo, thumbnail, descripción).",
      tags: ["classifier", "linkgrabber", "heuristics"],
      complexity: "moderate",
      lineRange: [20, 60]
    },
    {
      id: "function:src/jdownloader_mcp/youtube/filter.py:filter_collector_links",
      type: "function",
      name: "filter_collector_links",
      filePath: "src/jdownloader_mcp/youtube/filter.py",
      summary: "Elimina selectivamente audios sueltos del LinkCollector manteniendo subtítulos (.srt) y video.",
      tags: ["filter-execution", "batch-cleanup", "jdownloader"],
      complexity: "moderate",
      lineRange: [65, 108]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/diff.py",
      type: "file",
      name: "diff.py",
      filePath: "src/jdownloader_mcp/youtube/diff.py",
      summary: "Calcula diferencias incrementales entre la lista actual de videos de un canal y el catálogo local previo.",
      tags: ["incremental-diff", "comparator", "synchronization"],
      complexity: "simple"
    },
    {
      id: "class:src/jdownloader_mcp/youtube/diff.py:ResultadoDiff",
      type: "class",
      name: "ResultadoDiff",
      filePath: "src/jdownloader_mcp/youtube/diff.py",
      summary: "Estructura que categoriza videos nuevos, sin cambios o modificados en la sincronización.",
      tags: ["data-model", "diff", "dataclass"],
      complexity: "simple",
      lineRange: [12, 25]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/export.py",
      type: "file",
      name: "export.py",
      filePath: "src/jdownloader_mcp/youtube/export.py",
      summary: "Exporta catálogos de videos a archivos JSON organizados por canal, fecha e historial de sincronización.",
      tags: ["export", "json", "filesystem"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/youtube/pipeline.py",
      type: "file",
      name: "pipeline.py",
      filePath: "src/jdownloader_mcp/youtube/pipeline.py",
      summary: "Orquestador de alto nivel que coordina la extracción, detección de idioma, adición a JDownloader y filtrado de variantes.",
      tags: ["pipeline", "orchestration", "workflow"],
      complexity: "complex"
    },
    {
      id: "function:src/jdownloader_mcp/youtube/pipeline.py:add_youtube_video_smart",
      type: "function",
      name: "add_youtube_video_smart",
      filePath: "src/jdownloader_mcp/youtube/pipeline.py",
      summary: "Pipeline completo para un video individual: inyección, espera activa de variantes y filtrado de tracks.",
      tags: ["workflow", "pipeline", "smart-add"],
      complexity: "complex",
      lineRange: [45, 120]
    },
    {
      id: "function:src/jdownloader_mcp/youtube/pipeline.py:sync_youtube_channel_to_jd",
      type: "function",
      name: "sync_youtube_channel_to_jd",
      filePath: "src/jdownloader_mcp/youtube/pipeline.py",
      summary: "Pipeline de sincronización masiva: descarga catálogo de canal, calcula diff, exporta JSON y opcionalmente envía nuevos a JDownloader.",
      tags: ["channel-sync", "batch-pipeline", "incremental"],
      complexity: "complex",
      lineRange: [125, 218]
    },
    {
      id: "file:src/jdownloader_mcp/youtube/utils.py",
      type: "file",
      name: "utils.py",
      filePath: "src/jdownloader_mcp/youtube/utils.py",
      summary: "Utilidades auxiliares para normalización de handles, extracción de video IDs, formato de duraciones y sanitización.",
      tags: ["utility", "formatting", "helpers"],
      complexity: "simple"
    }
  ],
  edges: [
    { source: "file:src/jdownloader_mcp/youtube/__init__.py", target: "file:src/jdownloader_mcp/youtube/filter.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/__init__.py", target: "file:src/jdownloader_mcp/youtube/key_router.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/__init__.py", target: "file:src/jdownloader_mcp/youtube/language.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/__init__.py", target: "file:src/jdownloader_mcp/youtube/pipeline.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "function:src/jdownloader_mcp/youtube/api.py:get_channel_id", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "function:src/jdownloader_mcp/youtube/api.py:get_uploads_playlist_id", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "function:src/jdownloader_mcp/youtube/api.py:get_playlist_items", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "file:src/jdownloader_mcp/youtube/key_router.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "file:src/jdownloader_mcp/youtube/quota.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "file:src/jdownloader_mcp/youtube/language.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/api.py", target: "file:src/jdownloader_mcp/youtube/utils.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/key_router.py", target: "class:src/jdownloader_mcp/youtube/key_router.py:KeyRouter", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/quota.py", target: "function:src/jdownloader_mcp/youtube/quota.py:registrar_uso", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/language.py", target: "class:src/jdownloader_mcp/youtube/language.py:LanguageDetectionResult", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/language.py", target: "function:src/jdownloader_mcp/youtube/language.py:detect_video_language", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/filter.py", target: "function:src/jdownloader_mcp/youtube/filter.py:classify_youtube_link", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/filter.py", target: "function:src/jdownloader_mcp/youtube/filter.py:filter_collector_links", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/diff.py", target: "class:src/jdownloader_mcp/youtube/diff.py:ResultadoDiff", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/export.py", target: "file:src/jdownloader_mcp/youtube/utils.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "function:src/jdownloader_mcp/youtube/pipeline.py:add_youtube_video_smart", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "function:src/jdownloader_mcp/youtube/pipeline.py:sync_youtube_channel_to_jd", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/api.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/filter.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/diff.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/export.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/key_router.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/language.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/youtube/pipeline.py", target: "file:src/jdownloader_mcp/youtube/utils.py", type: "imports", weight: 0.7 }
  ]
};

// ==========================================
// BATCH 3: DOCKER INFRASTRUCTURE
// ==========================================
const batch3 = {
  nodes: [
    {
      id: "service:Dockerfile",
      type: "service",
      name: "Dockerfile",
      filePath: "Dockerfile",
      summary: "Imagen de contenedor Linux optimizada con Python y dependencias para ejecutar el servidor JDownloader MCP en entornos aislados.",
      tags: ["containerization", "docker", "deployment"],
      complexity: "simple"
    },
    {
      id: "config:.dockerignore",
      type: "config",
      name: ".dockerignore",
      filePath: ".dockerignore",
      summary: "Reglas de exclusión para la compilación de la imagen Docker (excluye entornos virtuales, cachés y artefactos git).",
      tags: ["docker", "configuration", "build-optimization"],
      complexity: "simple"
    }
  ],
  edges: [
    { source: "config:.dockerignore", target: "service:Dockerfile", type: "configures", weight: 0.8 }
  ]
};

// ==========================================
// BATCH 4: CI/CD WORKFLOWS
// ==========================================
const batch4 = {
  nodes: [
    {
      id: "pipeline:.github/workflows/docker-publish.yml",
      type: "pipeline",
      name: "docker-publish.yml",
      filePath: ".github/workflows/docker-publish.yml",
      summary: "Flujo de trabajo de GitHub Actions para construir y publicar automáticamente la imagen Docker en GitHub Container Registry.",
      tags: ["ci-cd", "github-actions", "container-registry", "deployment"],
      complexity: "moderate"
    }
  ],
  edges: [
    { source: "pipeline:.github/workflows/docker-publish.yml", target: "service:Dockerfile", type: "deploys", weight: 0.8 }
  ]
};

// ==========================================
// BATCH 5: CONFIGURATIONS & CORE DOCUMENTATION
// ==========================================
const batch5 = {
  nodes: [
    {
      id: "config:.env.example",
      type: "config",
      name: ".env.example",
      filePath: ".env.example",
      summary: "Plantilla de variables de entorno para credenciales My.JDownloader, claves YouTube v3 y API keys de solvers externos.",
      tags: ["configuration", "environment", "template"],
      complexity: "simple"
    },
    {
      id: "document:INSTALL_PROMPT.md",
      type: "document",
      name: "INSTALL_PROMPT.md",
      filePath: "INSTALL_PROMPT.md",
      summary: "Instrucciones de configuración paso a paso y prompt asistido para instalar y vincular JDownloader MCP en clientes de IA.",
      tags: ["documentation", "installation", "setup-guide"],
      complexity: "moderate"
    },
    {
      id: "document:README.md",
      type: "document",
      name: "README.md",
      filePath: "README.md",
      summary: "Documentación principal del proyecto: arquitectura del servidor, lista de 79 herramientas MCP, solvers de captcha y capacidades de YouTube.",
      tags: ["documentation", "entry-point", "architecture"],
      complexity: "complex"
    },
    {
      id: "document:SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md",
      type: "document",
      name: "SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md",
      filePath: "SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md",
      summary: "Propuesta arquitectónica y funcional detallada para el Sistema de Memoria Audiovisual de YouTube con IA, chunking temporal y búsqueda semántica.",
      tags: ["architecture", "specifications", "youtube-rag", "documentation"],
      complexity: "complex"
    },
    {
      id: "config:mcp_config.docker.json",
      type: "config",
      name: "mcp_config.docker.json",
      filePath: "mcp_config.docker.json",
      summary: "Configuración MCP para ejecutar el servidor mediante contenedor Docker.",
      tags: ["configuration", "mcp", "docker"],
      complexity: "simple"
    },
    {
      id: "config:mcp_config.json",
      type: "config",
      name: "mcp_config.json",
      filePath: "mcp_config.json",
      summary: "Configuración global de MCP para el cliente Gemini / Claude ejecutando el servidor desde el entorno virtual local.",
      tags: ["configuration", "mcp-client", "local-exec"],
      complexity: "simple"
    },
    {
      id: "config:mcp_config.uvx.json",
      type: "config",
      name: "mcp_config.uvx.json",
      filePath: "mcp_config.uvx.json",
      summary: "Configuración MCP para ejecución efímera mediante la herramienta uvx de uv.",
      tags: ["configuration", "uvx", "runner"],
      complexity: "simple"
    },
    {
      id: "config:pyproject.toml",
      type: "config",
      name: "pyproject.toml",
      filePath: "pyproject.toml",
      summary: "Definición del paquete Python con dependencias (myjdapi, mcp, google-api-python-client, pillow) y scripts de entrada.",
      tags: ["configuration", "packaging", "dependencies", "python"],
      complexity: "moderate"
    },
    {
      id: "config:requirements.txt",
      type: "config",
      name: "requirements.txt",
      filePath: "requirements.txt",
      summary: "Lista estándar de dependencias pip del proyecto para entornos legacy o despliegues en contenedores.",
      tags: ["dependencies", "pip", "configuration"],
      complexity: "simple"
    }
  ],
  edges: [
    { source: "document:README.md", target: "file:src/jdownloader_mcp/server.py", type: "documents", weight: 0.9 },
    { source: "document:SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md", target: "file:src/jdownloader_mcp/youtube/pipeline.py", type: "documents", weight: 0.8 },
    { source: "document:INSTALL_PROMPT.md", target: "config:mcp_config.json", type: "documents", weight: 0.7 },
    { source: "config:pyproject.toml", target: "file:src/jdownloader_mcp/server.py", type: "configures", weight: 0.8 },
    { source: "config:mcp_config.json", target: "file:src/jdownloader_mcp/server.py", type: "configures", weight: 0.8 }
  ]
};

// ==========================================
// BATCH 6: CLI, SKILLS & CAPTCHA ML PREPROCESSING
// ==========================================
const batch6 = {
  nodes: [
    {
      id: "file:cli_youtube.py",
      type: "file",
      name: "cli_youtube.py",
      filePath: "cli_youtube.py",
      summary: "Interfaz de línea de comandos para control directo de YouTube + JDownloader (subcomandos add, filter y sync).",
      tags: ["cli", "entry-point", "automation", "tool"],
      complexity: "moderate"
    },
    {
      id: "function:cli_youtube.py:cmd_add",
      type: "function",
      name: "cmd_add",
      filePath: "cli_youtube.py",
      summary: "Manejador del comando 'add' para inyectar y filtrar un video de YouTube con auto-arranque opcional.",
      tags: ["cli-handler", "download"],
      complexity: "simple",
      lineRange: [70, 90]
    },
    {
      id: "function:cli_youtube.py:cmd_filter",
      type: "function",
      name: "cmd_filter",
      filePath: "cli_youtube.py",
      summary: "Manejador del comando 'filter' para sanear el LinkGrabber eliminando pistas de audio sueltas.",
      tags: ["cli-handler", "filter"],
      complexity: "simple",
      lineRange: [92, 115]
    },
    {
      id: "function:cli_youtube.py:cmd_sync",
      type: "function",
      name: "cmd_sync",
      filePath: "cli_youtube.py",
      summary: "Manejador del comando 'sync' para sincronizar catálogos completos de canales de YouTube mediante diff.",
      tags: ["cli-handler", "sync"],
      complexity: "simple",
      lineRange: [117, 140]
    },
    {
      id: "document:skill/jdownloader-usage.md",
      type: "document",
      name: "jdownloader-usage.md",
      filePath: "skill/jdownloader-usage.md",
      summary: "Guía de uso práctico y ejemplos para el control de JDownloader mediante instrucciones en lenguaje natural.",
      tags: ["documentation", "user-guide", "skill"],
      complexity: "moderate"
    },
    {
      id: "document:skill/jdownloader.md",
      type: "document",
      name: "jdownloader.md",
      filePath: "skill/jdownloader.md",
      summary: "Especificación completa del skill de JDownloader con catálogo exhaustivo de herramientas, parámetros y patrones de uso.",
      tags: ["documentation", "skill-definition", "reference"],
      complexity: "complex"
    },
    {
      id: "file:src/jdownloader_mcp/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/__init__.py",
      summary: "Inicializador raíz del paquete Python jdownloader_mcp.",
      tags: ["package-root", "init"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/models/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/captcha_solver/models/__init__.py",
      summary: "Inicializador del submódulo de arquitecturas de modelos de redes neuronales.",
      tags: ["init", "models"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/models/cnn_model.py",
      type: "file",
      name: "cnn_model.py",
      filePath: "src/jdownloader_mcp/captcha_solver/models/cnn_model.py",
      summary: "Arquitectura PyTorch para red neuronal convolucional personalizada con función de pérdida multi-carácter para captchas.",
      tags: ["pytorch", "cnn", "deep-learning", "model-architecture"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/models/cnn_model.py:CaptchaCNN",
      type: "class",
      name: "CaptchaCNN",
      filePath: "src/jdownloader_mcp/captcha_solver/models/cnn_model.py",
      summary: "Red neuronal convolucional profunda para reconocimiento óptico de caracteres distorsionados.",
      tags: ["neural-network", "cnn", "pytorch"],
      complexity: "moderate",
      lineRange: [20, 110]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/preprocessing/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/captcha_solver/preprocessing/__init__.py",
      summary: "Inicializador del submódulo de preprocesamiento de imágenes.",
      tags: ["init", "preprocessing"],
      complexity: "simple"
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py",
      type: "file",
      name: "image_processor.py",
      filePath: "src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py",
      summary: "Pipeline de transformación de imágenes: binarización, eliminación de ruido de fondo, umbralizado Otsu y redimensionamiento.",
      tags: ["image-processing", "opencv", "computer-vision"],
      complexity: "moderate"
    },
    {
      id: "class:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py:ImageProcessor",
      type: "class",
      name: "ImageProcessor",
      filePath: "src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py",
      summary: "Procesador de imágenes con filtros morfológicos optimizados para mejorar la tasa de acierto de OCR y redes neuronales.",
      tags: ["filter-pipeline", "vision", "processor"],
      complexity: "moderate",
      lineRange: [15, 165]
    },
    {
      id: "file:src/jdownloader_mcp/captcha_solver/solvers/__init__.py",
      type: "file",
      name: "__init__.py",
      filePath: "src/jdownloader_mcp/captcha_solver/solvers/__init__.py",
      summary: "Carga dinámica con getattr lazy para importar resolutores sin penalización de arranque.",
      tags: ["lazy-loading", "solvers", "init"],
      complexity: "simple"
    }
  ],
  edges: [
    { source: "file:cli_youtube.py", target: "function:cli_youtube.py:cmd_add", type: "contains", weight: 1.0 },
    { source: "file:cli_youtube.py", target: "function:cli_youtube.py:cmd_filter", type: "contains", weight: 1.0 },
    { source: "file:cli_youtube.py", target: "function:cli_youtube.py:cmd_sync", type: "contains", weight: 1.0 },
    { source: "file:cli_youtube.py", target: "file:src/jdownloader_mcp/youtube/pipeline.py", type: "imports", weight: 0.7 },
    { source: "file:cli_youtube.py", target: "file:src/jdownloader_mcp/youtube/filter.py", type: "imports", weight: 0.7 },
    { source: "file:src/jdownloader_mcp/captcha_solver/models/cnn_model.py", target: "class:src/jdownloader_mcp/captcha_solver/models/cnn_model.py:CaptchaCNN", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py", target: "class:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py:ImageProcessor", type: "contains", weight: 1.0 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/models/cnn_model.py", type: "depends_on", weight: 0.8 },
    { source: "file:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py", target: "file:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py", type: "depends_on", weight: 0.8 },
    { source: "document:skill/jdownloader.md", target: "file:src/jdownloader_mcp/server.py", type: "documents", weight: 0.8 },
    { source: "document:skill/jdownloader-usage.md", target: "file:src/jdownloader_mcp/server.py", type: "documents", weight: 0.7 }
  ]
};

const allBatches = [
  { index: 1, data: batch1 },
  { index: 2, data: batch2 },
  { index: 3, data: batch3 },
  { index: 4, data: batch4 },
  { index: 5, data: batch5 },
  { index: 6, data: batch6 }
];

for (const b of allBatches) {
  const filePath = path.join(interDir, `batch-${b.index}.json`);
  fs.writeFileSync(filePath, JSON.stringify(b.data, null, 2));
  console.log(`Saved batch-${b.index}.json with ${b.data.nodes.length} nodes and ${b.data.edges.length} edges.`);
}
console.log('All 6 batch files created successfully!');
