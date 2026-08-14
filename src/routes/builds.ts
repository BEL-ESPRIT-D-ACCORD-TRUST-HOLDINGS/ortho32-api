import { FastifyInstance } from 'fastify';
import { randomUUID } from 'node:crypto';

interface Build {
  id: string;
  status: 'queued' | 'building' | 'success' | 'failed';
  target: string;
  cycles?: number;
  createdAt: string;
  logs: string[];
}

const builds = new Map<string, Build>();

export default async function buildRoutes(fastify: FastifyInstance) {
  fastify.post('/', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const body = request.body as any;
    const target = body?.target ?? 'ortho32';
    const id = randomUUID();
    const build: Build = {
      id,
      status: 'success',
      target,
      cycles: 2048, // integer cycles
      createdAt: new Date().toISOString(),
      logs: ['[build] queued', '[build] compiling', '[build] linking', '[build] success']
    };
    builds.set(id, build);
    // @ts-ignore
    return reply.code(201).envelope(build, 'build.created', 201);
  });

  fastify.get('/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const b = builds.get(id);
    if (!b) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'build not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(b, 'build.get');
  });

  fastify.get('/:id/logs', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const b = builds.get(id);
    if (!b) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'build not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope({ buildId: id, logs: b.logs }, 'build.logs');
  });
}
