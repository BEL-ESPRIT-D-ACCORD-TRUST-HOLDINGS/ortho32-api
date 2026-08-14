import { FastifyInstance } from 'fastify';

export default async function systemRoutes(fastify: FastifyInstance) {
  fastify.get('/status', async (request, reply) => {
    const data = {
      status: 'ok',
      uptime: process.uptime(),
      uptimeCycles: Math.floor(process.uptime() * 1000), // illustrative cycles derived from uptime, still integer
      fabric: 'online',
      devicesConnected: 2,
      version: '1.0.0'
    };
    // @ts-ignore
    return reply.envelope(data, 'system.status');
  });

  fastify.get('/version', async (request, reply) => {
    const data = {
      version: '1.0.0',
      apiVersion: 'v1',
      build: process.env.BUILD_ID || 'dev',
      protocol: 'ortho32-api',
      transports: ['http', 'ipc']
    };
    // @ts-ignore
    return reply.envelope(data, 'system.version');
  });
}
