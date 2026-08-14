import { FastifyInstance } from 'fastify';
import { randomUUID } from 'node:crypto';

const agents = [
  { id: 'verify', name: 'Verify Agent', status: 'idle' as const, capabilities: ['proofs.verify'] },
  { id: 'fabric', name: 'Fabric Agent', status: 'idle' as const, capabilities: ['fabric.commands'] },
  { id: 'tensor', name: 'Tensor Agent', status: 'running' as const, capabilities: ['tensor.jobs'] }
];

const tasks = new Map<string, any>();

export default async function agentRoutes(fastify: FastifyInstance) {
  fastify.get('/', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(agents, 'agents.list');
  });

  fastify.post('/:id/tasks', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const agent = agents.find((a) => a.id === id);
    if (!agent) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'agent not found' }, 'error.not_found', 404);
    }
    const body = request.body as any;
    const taskId = randomUUID();
    const task = {
      id: taskId,
      agentId: id,
      type: body?.type ?? 'generic',
      status: 'completed' as const,
      input: body?.input ?? body,
      output: { result: 'ok' },
      cycles: 64,
      createdAt: new Date().toISOString()
    };
    tasks.set(taskId, task);
    // @ts-ignore
    return reply.code(201).envelope(task, 'agents.task.created', 201);
  });

  fastify.get('/:id/tasks/:taskId', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { taskId } = request.params as { id: string; taskId: string };
    const task = tasks.get(taskId);
    if (!task) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'task not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(task, 'agents.task.get');
  });
}
