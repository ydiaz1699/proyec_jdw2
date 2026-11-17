const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const projectRoot = 'C:/Users/Alex/Desktop/1-Github/proyec_jdw2';
const uaDir = path.join(projectRoot, '.ua');
const interDir = path.join(uaDir, 'intermediate');

const assembledPath = path.join(interDir, 'assembled-graph.json');
const assembled = JSON.parse(fs.readFileSync(assembledPath, 'utf8'));

// Get current git commit hash
let gitCommitHash = '0000000000000000000000000000000000000000';
try {
  gitCommitHash = execSync('git rev-parse HEAD', { cwd: projectRoot, encoding: 'utf8' }).trim();
} catch (e) {
  console.log('Using default git hash:', e.message);
}

const layers = [
  {
    id: "layer:mcp-core-interface",
    name: "Servidor MCP e Interfaces de Control",
    description: "Puntos de entrada que exponen el servidor FastMCP con 79 herramientas para clientes de IA y la interfaz CLI para scripts locales.",
    nodeIds: [
      "file:src/jdownloader_mcp/server.py",
      "file:src/jdownloader_mcp/__init__.py",
      "file:cli_youtube.py"
    ]
  },
  {
    id: "layer:youtube-engine",
    name: "Motor de YouTube y Pipeline Audiovisual",
    description: "Módulo especializado en extracción por YouTube Data API v3, rotación multi-clave de cuota, detección de idioma y filtrado inteligente de variantes conservando subtítulos.",
    nodeIds: [
      "file:src/jdownloader_mcp/youtube/__init__.py",
      "file:src/jdownloader_mcp/youtube/api.py",
      "file:src/jdownloader_mcp/youtube/key_router.py",
      "file:src/jdownloader_mcp/youtube/quota.py",
      "file:src/jdownloader_mcp/youtube/language.py",
      "file:src/jdownloader_mcp/youtube/filter.py",
      "file:src/jdownloader_mcp/youtube/diff.py",
      "file:src/jdownloader_mcp/youtube/export.py",
      "file:src/jdownloader_mcp/youtube/pipeline.py",
      "file:src/jdownloader_mcp/youtube/utils.py"
    ]
  },
  {
    id: "layer:captcha-subsystem",
    name: "Subsistema de Resolución de Captchas",
    description: "Arquitectura modular para resolución de desafíos de JDownloader con enrutamiento dinámico, demonio en segundo plano, OCR, redes neuronales CNN y servicios remotos.",
    nodeIds: [
      "file:src/jdownloader_mcp/captcha_solver/__init__.py",
      "file:src/jdownloader_mcp/captcha_solver/base.py",
      "file:src/jdownloader_mcp/captcha_solver/router.py",
      "file:src/jdownloader_mcp/captcha_solver/daemon.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/darknet_solver.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/ml_solver.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/nopecha_solver.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/ocr_solver.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/twocaptcha_solver.py",
      "file:src/jdownloader_mcp/captcha_solver/models/__init__.py",
      "file:src/jdownloader_mcp/captcha_solver/models/cnn_model.py",
      "file:src/jdownloader_mcp/captcha_solver/preprocessing/__init__.py",
      "file:src/jdownloader_mcp/captcha_solver/preprocessing/image_processor.py",
      "file:src/jdownloader_mcp/captcha_solver/solvers/__init__.py"
    ]
  },
  {
    id: "layer:infra-deployment",
    name: "Infraestructura, Empaquetado y Configuración",
    description: "Definición de paquetes, dependencias, variables de entorno, manifiestos MCP y contenedores Docker para distribución y despliegue CI/CD.",
    nodeIds: [
      "service:Dockerfile",
      "config:.dockerignore",
      "pipeline:.github/workflows/docker-publish.yml",
      "config:pyproject.toml",
      "config:requirements.txt",
      "config:mcp_config.docker.json",
      "config:mcp_config.json",
      "config:mcp_config.uvx.json",
      "config:.env.example"
    ]
  },
  {
    id: "layer:docs-knowledge",
    name: "Documentación, Habilidades y Especificaciones",
    description: "Documentación integral del servidor, especificaciones técnicas del sistema de memoria audiovisual propuesto y definiciones de habilidades para agentes.",
    nodeIds: [
      "document:README.md",
      "document:INSTALL_PROMPT.md",
      "document:SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md",
      "document:skill/jdownloader-usage.md",
      "document:skill/jdownloader.md"
    ]
  }
];

const tour = [
  {
    order: 1,
    title: "1. Visión General del Proyecto y Capacidades",
    description: "Comienza revisando el README y la guía de instalación para comprender cómo se orquesta JDownloader de forma remota y cómo se integran las 79 herramientas MCP.",
    nodeIds: ["document:README.md", "document:INSTALL_PROMPT.md"]
  },
  {
    order: 2,
    title: "2. Servidor FastMCP y Gestión de Estado",
    description: "server.py es el núcleo del proyecto. Examina la clase JDState y cómo se registran las herramientas de conexión, descargas, captchas y filtrado inteligente.",
    nodeIds: ["file:src/jdownloader_mcp/server.py"]
  },
  {
    order: 3,
    title: "3. Motor Inteligente de YouTube y Filtrado",
    description: "Explora la integración con YouTube Data API v3 y el pipeline que clasifica paquetes conservando video, carátula y subtítulos .srt en cualquier idioma.",
    nodeIds: [
      "file:src/jdownloader_mcp/youtube/pipeline.py",
      "file:src/jdownloader_mcp/youtube/api.py",
      "file:src/jdownloader_mcp/youtube/filter.py"
    ]
  },
  {
    order: 4,
    title: "4. Rotación Multi-Clave y Resiliencia de Cuota",
    description: "Descubre cómo KeyRouter y quota.py gestionan múltiples API keys de YouTube rotando dinámicamente cuando se agotan los 10,000 puntos diarios.",
    nodeIds: [
      "file:src/jdownloader_mcp/youtube/key_router.py",
      "file:src/jdownloader_mcp/youtube/quota.py"
    ]
  },
  {
    order: 5,
    title: "5. Subsistema de Resolución de Captchas",
    description: "Inspecciona la arquitectura de resolución de captchas con su daemon automático, router de fallover y resolutores locales (OCR, CNN) y remotos (2Captcha, NopeCHA).",
    nodeIds: [
      "file:src/jdownloader_mcp/captcha_solver/router.py",
      "file:src/jdownloader_mcp/captcha_solver/daemon.py",
      "file:src/jdownloader_mcp/captcha_solver/base.py"
    ]
  },
  {
    order: 6,
    title: "6. Herramienta de Línea de Comandos (CLI)",
    description: "cli_youtube.py permite sincronizar canales completos y filtrar links de JDownloader sin necesidad de ejecutar un cliente LLM completo.",
    nodeIds: ["file:cli_youtube.py"]
  },
  {
    order: 7,
    title: "7. Especificación Futura: Memoria Audiovisual RAG",
    description: "Conoce el diseño técnico para convertir videos descargados en una biblioteca de conocimiento consultable con timestamps exactos y chunking semántico.",
    nodeIds: [
      "document:skill/jdownloader.md",
      "document:SISTEMA_MEMORIA_AUDIOVISUAL_PROPUESTA.md"
    ]
  }
];

const fullKnowledgeGraph = {
  version: "1.0.0",
  project: {
    name: "proyec_jdw2",
    languages: ["python", "markdown", "dockerfile", "yaml", "json", "toml"],
    frameworks: ["FastMCP", "PyTorch"],
    description: "Servidor MCP integral para control remoto de JDownloader con 79 herramientas, auto-resolución de captchas, motor de YouTube inteligente con rotación de claves y preservación de subtítulos.",
    analyzedAt: new Date().toISOString(),
    gitCommitHash: gitCommitHash
  },
  nodes: assembled.nodes,
  edges: assembled.edges,
  layers: layers,
  tour: tour
};

// Write assembled full graph
fs.writeFileSync(assembledPath, JSON.stringify(fullKnowledgeGraph, null, 2));
console.log('Assembled full KnowledgeGraph written to', assembledPath);

// Create inline validation script
const validateScript = `#!/usr/bin/env node
const fs = require('fs');
const graphPath = process.argv[2];
const outputPath = process.argv[3];
try {
  const graph = JSON.parse(fs.readFileSync(graphPath, 'utf8'));
  const issues = [], warnings = [];
  if (!Array.isArray(graph.nodes)) { issues.push('graph.nodes is missing or not an array'); graph.nodes = []; }
  if (!Array.isArray(graph.edges)) { issues.push('graph.edges is missing or not an array'); graph.edges = []; }
  const nodeIds = new Set();
  const seen = new Map();
  graph.nodes.forEach((n, i) => {
    if (!n.id) { issues.push(\`Node[\${i}] missing id\`); return; }
    if (!n.type) issues.push(\`Node[\${i}] '\${n.id}' missing type\`);
    if (!n.name) issues.push(\`Node[\${i}] '\${n.id}' missing name\`);
    if (!n.summary) issues.push(\`Node[\${i}] '\${n.id}' missing summary\`);
    if (!n.tags || !n.tags.length) issues.push(\`Node[\${i}] '\${n.id}' missing tags\`);
    if (seen.has(n.id)) issues.push(\`Duplicate node ID '\${n.id}' at indices \${seen.get(n.id)} and \${i}\`);
    else seen.set(n.id, i);
    nodeIds.add(n.id);
  });
  graph.edges.forEach((e, i) => {
    if (!nodeIds.has(e.source)) issues.push(\`Edge[\${i}] source '\${e.source}' not found\`);
    if (!nodeIds.has(e.target)) issues.push(\`Edge[\${i}] target '\${e.target}' not found\`);
  });
  const fileLevelTypes = new Set(['file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint']);
  const fileNodes = graph.nodes.filter(n => fileLevelTypes.has(n.type)).map(n => n.id);
  const assigned = new Map();
  if (!Array.isArray(graph.layers)) { if (graph.layers) warnings.push('graph.layers is not an array'); graph.layers = []; }
  if (!Array.isArray(graph.tour)) { if (graph.tour) warnings.push('graph.tour is not an array'); graph.tour = []; }
  graph.layers.forEach(layer => {
    (layer.nodeIds || []).forEach(id => {
      if (!nodeIds.has(id)) issues.push(\`Layer '\${layer.id}' refs missing node '\${id}'\`);
      if (assigned.has(id)) issues.push(\`Node '\${id}' appears in multiple layers\`);
      assigned.set(id, layer.id);
    });
  });
  fileNodes.forEach(id => {
    if (!assigned.has(id)) issues.push(\`File node '\${id}' not in any layer\`);
  });
  graph.tour.forEach((step, i) => {
    (step.nodeIds || []).forEach(id => {
      if (!nodeIds.has(id)) issues.push(\`Tour step[\${i}] refs missing node '\${id}'\`);
    });
  });
  const withEdges = new Set([
    ...graph.edges.map(e => e.source),
    ...graph.edges.map(e => e.target)
  ]);
  graph.nodes.forEach(n => {
    if (!withEdges.has(n.id)) warnings.push(\`Node '\${n.id}' has no edges (orphan)\`);
  });
  const stats = {
    totalNodes: graph.nodes.length,
    totalEdges: graph.edges.length,
    totalLayers: graph.layers.length,
    tourSteps: graph.tour.length,
    nodeTypes: graph.nodes.reduce((a, n) => { a[n.type] = (a[n.type]||0)+1; return a; }, {}),
    edgeTypes: graph.edges.reduce((a, e) => { a[e.type] = (a[e.type]||0)+1; return a; }, {})
  };
  fs.writeFileSync(outputPath, JSON.stringify({ issues, warnings, stats }, null, 2));
  console.log('Inline validation complete. Issues:', issues.length, 'Warnings:', warnings.length);
  process.exit(0);
} catch (err) { process.stderr.write(err.message + '\\n'); process.exit(1); }
`;

const validateScriptPath = path.join(uaDir, 'tmp', 'ua-inline-validate.cjs');
fs.writeFileSync(validateScriptPath, validateScript);
console.log('Wrote inline validation script.');

// Run inline validation
const reviewOutputPath = path.join(interDir, 'review.json');
execSync(`node "${validateScriptPath}" "${assembledPath}" "${reviewOutputPath}"`, { stdio: 'inherit' });

// Also run @understand-anything/core validateGraph
const core = require('C:/SKILL_config/Understand-Anything/understand-anything-plugin/packages/core/dist/index.js');
const coreValidation = core.validateGraph(fullKnowledgeGraph);
console.log('Core validateGraph success:', coreValidation.success);
if (!coreValidation.success) {
  console.log('Core errors:', coreValidation.errors);
}

// Phase 7: SAVE knowledge-graph.json
const finalGraphPath = path.join(uaDir, 'knowledge-graph.json');
fs.writeFileSync(finalGraphPath, JSON.stringify(fullKnowledgeGraph, null, 2));
console.log('Final knowledge-graph.json written successfully.');

// Phase 7: Build fingerprints baseline
const scanResult = JSON.parse(fs.readFileSync(path.join(interDir, 'scan-result.json'), 'utf8'));
const fingerprintInput = {
  projectRoot: projectRoot,
  filePaths: scanResult.files.map(f => f.path),
  gitCommitHash: gitCommitHash
};
const fpInputPath = path.join(interDir, 'fingerprint-input.json');
fs.writeFileSync(fpInputPath, JSON.stringify(fingerprintInput, null, 2));
console.log('Wrote fingerprint input for', fingerprintInput.filePaths.length, 'files.');

console.log('Running build-fingerprints.mjs...');
execSync(`node "C:/SKILL_config/Understand-Anything/understand-anything-plugin/skills/understand/build-fingerprints.mjs" "${fpInputPath}"`, { stdio: 'inherit' });

// Phase 7: Save meta.json
const meta = {
  lastAnalyzedAt: new Date().toISOString(),
  gitCommitHash: gitCommitHash,
  version: "1.0.0",
  project: {
    name: "proyec_jdw2",
    filesCount: scanResult.files.length,
    nodesCount: fullKnowledgeGraph.nodes.length,
    edgesCount: fullKnowledgeGraph.edges.length,
    layersCount: fullKnowledgeGraph.layers.length,
    tourStepsCount: fullKnowledgeGraph.tour.length
  }
};
fs.writeFileSync(path.join(uaDir, 'meta.json'), JSON.stringify(meta, null, 2));
console.log('meta.json saved successfully.');

// Save config.json with outputLanguage: "es"
const config = {
  outputLanguage: "es",
  autoUpdate: false
};
fs.writeFileSync(path.join(uaDir, 'config.json'), JSON.stringify(config, null, 2));
console.log('config.json saved with outputLanguage: es.');
