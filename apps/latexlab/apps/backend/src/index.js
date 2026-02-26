import Fastify from 'fastify';
import cors from '@fastify/cors';
import multipart from '@fastify/multipart';
// import websocket from '@fastify/websocket'; // collab disabled
import './config/loadEnv.js';
import { ensureDir } from './utils/fsUtils.js';
import { DATA_DIR, PORT } from './config/constants.js';
import { registerHealthRoutes } from './routes/health.js';
import { registerArxivRoutes } from './routes/arxiv.js';
import { registerProjectRoutes } from './routes/projects.js';
import { registerCompileRoutes } from './routes/compile.js';
import { registerLLMRoutes } from './routes/llm.js';
import { registerVisionRoutes } from './routes/vision.js';
import { registerPlotRoutes } from './routes/plot.js';
import { registerAgentRoutes } from './routes/agent.js';
// import { registerCollabRoutes } from './routes/collab.js'; // collab disabled
import { registerTransferRoutes } from './routes/transfer.js';
// import { tryStartTunnel } from './services/tunnel.js'; // collab disabled
// import { requireAuthIfRemote } from './utils/authUtils.js'; // collab disabled
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { existsSync } from 'node:fs';

const fastify = Fastify({ logger: true });

await fastify.register(cors, { origin: true });
await fastify.register(multipart, {
  limits: {
    fileSize: 200 * 1024 * 1024
  }
});
// --- Collaboration feature (disabled for now) ---
// await fastify.register(websocket);
// fastify.decorateRequest('collabAuth', null);
//
// fastify.addHook('preHandler', async (req, reply) => {
//   if (!req.url.startsWith('/api')) return;
//   if (req.method === 'OPTIONS') return;
//   if (req.url.startsWith('/api/health')) return;
//   if (req.url.startsWith('/api/collab')) return;
//   const auth = requireAuthIfRemote(req);
//   if (!auth.ok) {
//     reply.code(401).send({ ok: false, error: 'Unauthorized' });
//   }
//   req.collabAuth = auth.payload || null;
// });

registerHealthRoutes(fastify);
registerArxivRoutes(fastify);
registerProjectRoutes(fastify);
registerCompileRoutes(fastify);
registerLLMRoutes(fastify);
registerVisionRoutes(fastify);
registerPlotRoutes(fastify);
registerAgentRoutes(fastify);
// registerCollabRoutes(fastify); // collab disabled
registerTransferRoutes(fastify);

// Serve frontend static files in tunnel/production mode
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const frontendDist = join(__dirname, '../../frontend/dist');

if (existsSync(frontendDist)) {
  const fastifyStatic = await import('@fastify/static');
  await fastify.register(fastifyStatic.default, {
    root: frontendDist,
    prefix: '/',
    wildcard: false,
  });

  // SPA fallback: serve index.html for non-API routes
  fastify.setNotFoundHandler((req, reply) => {
    if (req.url.startsWith('/api')) {
      reply.code(404).send({ error: 'Not Found' });
    } else {
      reply.sendFile('index.html');
    }
  });
}

await ensureDir(DATA_DIR);

await fastify.listen({ port: PORT, host: '0.0.0.0' });

console.log('');
console.log(`  LatexLab started at http://localhost:${PORT}`);
console.log('');

// --- Tunnel / remote collaboration (disabled for now) ---
// const tunnelMode = TUNNEL_MODE.toLowerCase().trim();
// if (tunnelMode !== 'false' && tunnelMode !== '0' && tunnelMode !== 'no') {
//   const result = await tryStartTunnel(PORT);
//   if (result) {
//     console.log(`  Tunnel active (${result.provider}): ${result.url}`);
//   }
// }
