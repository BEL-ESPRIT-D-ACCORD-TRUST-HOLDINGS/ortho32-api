import { FastifyInstance } from 'fastify';

const devices = [
  { id: 'ortho0', name: 'ORTHO-32 DevKit #0', status: 'connected' as const, kind: 'ortho32' as const, fabricId: 'fabric-0', capabilities: ['tensor', 'trace'], lastSeen: new Date().toISOString() },
  { id: 'sim0', name: 'Simulated Device', status: 'disconnected' as const, kind: 'simulated' as const, fabricId: 'fabric-sim', capabilities: ['simulate'], lastSeen: new Date().toISOString() }
];

export default async function deviceRoutes(fastify: FastifyInstance) {
  fastify.get('/', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(devices, 'devices.list');
  });

  fastify.get('/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const dev = devices.find((d) => d.id === id);
    if (!dev) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'device not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(dev, 'devices.get');
  });

  fastify.post('/:id/connect', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const dev = devices.find((d) => d.id === id);
    if (!dev) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'device not found' }, 'error.not_found', 404);
    }
    (dev as any).status = 'connected';
    // @ts-ignore
    return reply.envelope({ id, status: 'connected' }, 'devices.connected');
  });

  fastify.post('/:id/disconnect', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const dev = devices.find((d) => d.id === id);
    if (!dev) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'device not found' }, 'error.not_found', 404);
    }
    (dev as any).status = 'disconnected';
    // @ts-ignore
    return reply.envelope({ id, status: 'disconnected' }, 'devices.disconnected');
  });

  fastify.post(
    '/:id/reset',
    { preHandler: [(fastify as any).authorize('hardware.reset')] },
    async (request, reply) => {
      const { id } = request.params as { id: string };
      const dev = devices.find((d) => d.id === id);
      if (!dev) {
        // @ts-ignore
        return reply.code(404).envelope({ error: 'device not found' }, 'error.not_found', 404);
      }
      (dev as any).status = 'resetting';
      setTimeout(() => {
        (dev as any).status = 'connected';
      }, 50);
      // @ts-ignore
      return reply.envelope({ id, status: 'resetting', cycles: 128 }, 'devices.reset');
    }
  );
}
