import { FastifyInstance } from 'fastify';

const packages = [
  { id: 'ortho.tensor', name: 'Tensor Toolkit', version: '0.4.1', description: 'Tensor ops for ORTHO-32', author: 'ortho', installed: false },
  { id: 'ortho.proofs.stdlib', name: 'Proof Stdlib', version: '1.2.0', description: 'Standard proof library', author: 'ortho', installed: true },
  { id: 'foo', name: 'Foo Package', version: '0.1.0', description: 'Example package', author: 'community', installed: false }
];

export default async function marketplaceRoutes(fastify: FastifyInstance) {
  fastify.get('/packages', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(packages, 'marketplace.packages');
  });

  fastify.get('/packages/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const pkg = packages.find((p) => p.id === id);
    if (!pkg) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'package not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(pkg, 'marketplace.package.get');
  });

  fastify.post(
    '/packages/:id/install',
    { preHandler: [(fastify as any).authorize('marketplace.install')] },
    async (request, reply) => {
      const { id } = request.params as { id: string };
      const pkg = packages.find((p) => p.id === id);
      if (!pkg) {
        // @ts-ignore
        return reply.code(404).envelope({ error: 'package not found' }, 'error.not_found', 404);
      }
      pkg.installed = true;
      // @ts-ignore
      return reply.envelope({ id, installed: true, version: pkg.version }, 'marketplace.package.installed');
    }
  );
}
