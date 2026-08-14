import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyJwt from '@fastify/jwt';
import envelopePlugin from './middleware/envelope.js';
import authPlugin from './middleware/auth.js';

import systemRoutes from './routes/system.js';
import authRoutes from './routes/auth.js';
import deviceRoutes from './routes/devices.js';
import fabricRoutes from './routes/fabric.js';
import tensorRoutes from './routes/tensor.js';
import proofRoutes from './routes/proofs.js';
import buildRoutes from './routes/builds.js';
import traceRoutes from './routes/traces.js';
import agentRoutes from './routes/agents.js';
import appRoutes from './routes/apps.js';
import marketplaceRoutes from './routes/marketplace.js';
import workspaceRoutes from './routes/workspaces.js';
import eventRoutes from './routes/events.js';
import aiRoutes from './routes/ai.js';

const PORT = parseInt(process.env.PORT || process.env.ORTHO_API_PORT || '7032', 10);
const HOST = process.env.HOST || '0.0.0.0';

export async function buildServer() {
  const fastify = Fastify({
    logger: true,
    trustProxy: true
  });

  await fastify.register(cors, {
    origin: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Correlation-ID'],
    exposedHeaders: ['X-Correlation-ID']
  });

  await fastify.register(fastifyJwt, {
    secret: process.env.ORTHO_JWT_SECRET || 'dev-only-secret-change-in-production-do-not-use',
    sign: { expiresIn: '8h' }
  });

  await fastify.register(envelopePlugin);
  await fastify.register(authPlugin);

  // Health check outside envelope for LB
  fastify.get('/health', async () => ({ ok: true }));

  // Versioned API routers
  await fastify.register(systemRoutes, { prefix: '/api/v1/system' });
  await fastify.register(authRoutes, { prefix: '/api/v1/auth' });
  await fastify.register(deviceRoutes, { prefix: '/api/v1/devices' });
  await fastify.register(fabricRoutes, { prefix: '/api/v1/fabric' });
  await fastify.register(tensorRoutes, { prefix: '/api/v1/tensor' });
  await fastify.register(proofRoutes, { prefix: '/api/v1/proofs' });
  await fastify.register(buildRoutes, { prefix: '/api/v1/builds' });
  await fastify.register(traceRoutes, { prefix: '/api/v1/traces' });
  await fastify.register(agentRoutes, { prefix: '/api/v1/agents' });
  await fastify.register(appRoutes, { prefix: '/api/v1/apps' });
  await fastify.register(marketplaceRoutes, { prefix: '/api/v1/marketplace' });
  await fastify.register(workspaceRoutes, { prefix: '/api/v1/workspaces' });
  await fastify.register(eventRoutes, { prefix: '/api/v1/events' });
  await fastify.register(aiRoutes, { prefix: '/api/v1/ai' });

  // 404 handler with envelope
  fastify.setNotFoundHandler((request, reply) => {
    // @ts-ignore envelope decorator
    return reply.code(404).envelope(null, 'error.not_found');
  });

  return fastify;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const server = await buildServer();
  try {
    await server.listen({ port: PORT, host: HOST });
    console.log(`ortho32-api listening on ${HOST}:${PORT}`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
}
