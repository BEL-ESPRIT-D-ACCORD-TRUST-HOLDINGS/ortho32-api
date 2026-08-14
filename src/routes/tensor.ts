import { FastifyInstance } from 'fastify';
import { TensorJobCreateSchema } from '../schemas/index.js';
import { randomUUID } from 'node:crypto';

interface TensorJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  model: string;
  cycles: number;
  createdAt: string;
  completedAt?: string;
  inputShape?: number[];
  result?: unknown;
}

const jobs = new Map<string, TensorJob>();

export default async function tensorRoutes(fastify: FastifyInstance) {
  fastify.post('/jobs', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = TensorJobCreateSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const input = parsed.data;
    const id = randomUUID();
    // cycles is integer architectural cost - simulated deterministically from model name length
    const cycles = Math.floor(input.model.length * 128 + 64);
    const job: TensorJob = {
      id,
      status: 'completed',
      model: input.model,
      cycles, // integer
      createdAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      inputShape: input.inputShape,
      result: { outputShape: input.inputShape ?? [1, 512] }
    };
    jobs.set(id, job);
    // @ts-ignore
    return reply.code(201).envelope(job, 'tensor.job.created', 201);
  });

  fastify.get('/jobs/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const job = jobs.get(id);
    if (!job) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'job not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(job, 'tensor.job');
  });

  fastify.get('/jobs/:id/trace', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const job = jobs.get(id);
    if (!job) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'job not found' }, 'error.not_found', 404);
    }
    const trace = {
      jobId: id,
      cycles: job.cycles, // integer, architectural
      records: [
        { cycleNumber: 0, timestamp: new Date().toISOString(), fabricState: 'dispatch' },
        { cycleNumber: job.cycles, timestamp: new Date().toISOString(), fabricState: 'complete' }
      ]
    };
    // @ts-ignore
    return reply.envelope(trace, 'tensor.job.trace');
  });
}
