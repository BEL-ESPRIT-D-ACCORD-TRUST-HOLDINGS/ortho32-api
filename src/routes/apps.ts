import { FastifyInstance } from 'fastify';

const apps = [
  { id: 'org.ortho.files', name: 'Files', route: 'ortho://app/files', version: '1.0.0' },
  { id: 'org.ortho.browser', name: 'Browser', route: 'ortho://app/browser', version: '1.0.0' },
  { id: 'org.ortho.ide', name: 'IDE', route: 'ortho://app/ide', version: '1.0.0' },
  { id: 'org.ortho.terminal', name: 'Terminal', route: 'ortho://app/terminal', version: '1.0.0' },
  { id: 'org.ortho.marketplace', name: 'Marketplace', route: 'ortho://app/marketplace', version: '1.0.0' },
  { id: 'org.ortho.settings', name: 'Settings', route: 'ortho://app/settings', version: '1.0.0' },
  { id: 'org.ortho.proofs', name: 'Proofs', route: 'ortho://app/proofs', version: '1.0.0' },
  { id: 'org.ortho.hardware', name: 'Hardware', route: 'ortho://app/hardware', version: '1.0.0' },
  { id: 'org.ortho.agents', name: 'Agents', route: 'ortho://app/agents', version: '1.0.0' },
  { id: 'org.ortho.activity', name: 'Activity', route: 'ortho://app/activity', version: '1.0.0' }
];

export default async function appRoutes(fastify: FastifyInstance) {
  fastify.get('/', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(apps, 'apps.list');
  });

  fastify.post('/:id/open', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const app = apps.find((a) => a.id === id);
    if (!app) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'app not found' }, 'error.not_found', 404);
    }
    const result = { appId: id, route: app.route, opened: true, windowId: `win-${Date.now()}` };
    // @ts-ignore
    return reply.envelope(result, 'apps.opened');
  });
}
