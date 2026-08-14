import { FastifyInstance } from 'fastify';
import { TraceCaptureRequestSchema } from '../schemas/index.js';
import { randomUUID } from 'node:crypto';

interface CycleRecord {
  cycleNumber: number; // integer
  timestamp: string;
  signals?: Record<string, unknown>;
}

interface Trace {
  id: string;
  status: 'capturing' | 'completed' | 'failed';
  cycles: number; // integer
  records: CycleRecord[];
  createdAt: string;
}

const traces = new Map<string, Trace>();

export default async function traceRoutes(fastify: FastifyInstance) {
  fastify.post('/capture', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = TraceCaptureRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const { durationCycles } = parsed.data;
    const id = randomUUID();
    const cycles = durationCycles ?? 256;
    const records: CycleRecord[] = Array.from({ length: Math.min(cycles, 10) }, (_, i) => ({
      cycleNumber: i,
      timestamp: new Date().toISOString(),
      signals: { fabric: 'idle' }
    }));
    // ensure final record aligns to cycles
    if (records.length > 0) records[records.length - 1].cycleNumber = cycles - 1;

    const trace: Trace = {
      id,
      status: 'completed',
      cycles, // integer
      records,
      createdAt: new Date().toISOString()
    };
    traces.set(id, trace);
    // @ts-ignore
    return reply.code(201).envelope(trace, 'trace.captured', 201);
  });

  fastify.get('/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const t = traces.get(id);
    if (!t) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'trace not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(t, 'trace.get');
  });

  fastify.post('/:id/replay', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const t = traces.get(id);
    if (!t) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'trace not found' }, 'error.not_found', 404);
    }
    const result = { traceId: id, replayId: randomUUID(), cycles: t.cycles, status: 'replayed' };
    // @ts-ignore
    return reply.envelope(result, 'trace.replayed');
  });

  fastify.post('/compare', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const body = request.body as any;
    const { a, b } = body ?? {};
    if (!a || !b) {
      // @ts-ignore
      return reply.code(400).envelope({ error: 'a and b trace ids required' }, 'error.validation', 400);
    }
    const traceA = traces.get(a);
    const traceB = traces.get(b);
    if (!traceA || !traceB) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'one or both traces not found' }, 'error.not_found', 404);
    }
    const diff = {
      a,
      b,
      cyclesA: traceA.cycles,
      cyclesB: traceB.cycles,
      deltaCycles: traceA.cycles - traceB.cycles, // integer
      mismatchedCycles: [] as number[]
    };
    // @ts-ignore
    return reply.envelope(diff, 'trace.compare');
  });
}
