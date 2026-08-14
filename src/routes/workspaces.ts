import { FastifyInstance } from 'fastify';

const workspaces = [
  { id: 'fabric', name: 'Fabric Workspace', routes: ['ortho://app/hardware', 'ortho://trace/cycle/420'], current: true },
  { id: 'ide', name: 'IDE Workspace', routes: ['ortho://ide/file/RTL.lean', 'ortho://terminal/session/19'], current: false }
];

export default async function workspaceRoutes(fastify: FastifyInstance) {
  fastify.get('/', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(workspaces, 'workspaces.list');
  });

  fastify.get('/current', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const current = workspaces.find((w) => w.current) ?? workspaces[0];
    // @ts-ignore
    return reply.envelope(current, 'workspaces.current');
  });

  fastify.post('/:id/open', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const ws = workspaces.find((w) => w.id === id);
    if (!ws) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'workspace not found' }, 'error.not_found', 404);
    }
    workspaces.forEach((w) => (w.current = w.id === id));
    // @ts-ignore
    return reply.envelope({ id, opened: true, routes: ws.routes }, 'workspaces.opened');
  });
}
