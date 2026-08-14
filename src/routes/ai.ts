import { FastifyInstance } from 'fastify';
import { AiConverseRequestSchema, AiInvokeRequestSchema } from '../schemas/index.js';
import { randomUUID } from 'node:crypto';

const models = [
  { id: 'ortho-llm-32', name: 'ORTHO LLM 32B', provider: 'ortho', contextWindow: 32768 },
  { id: 'ortho-embed-1', name: 'ORTHO Embed', provider: 'ortho', contextWindow: 8192 }
];

const providers = [
  { id: 'ortho', name: 'ORTHO Native', status: 'online' },
  { id: 'sim', name: 'Simulated Provider', status: 'offline' }
];

export default async function aiRoutes(fastify: FastifyInstance) {
  fastify.post('/converse', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = AiConverseRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const { messages, model } = parsed.data;
    const last = messages[messages.length - 1];
    const response = {
      id: randomUUID(),
      model: model ?? 'ortho-llm-32',
      message: { role: 'assistant', content: `Echo: ${last.content}` },
      cycles: 16
    };
    // @ts-ignore
    return reply.envelope(response, 'ai.converse');
  });

  fastify.post('/invoke', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = AiInvokeRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const { task } = parsed.data;
    const result = { id: randomUUID(), task, status: 'completed', output: { result: `invoked ${task}` }, cycles: 32 };
    // @ts-ignore
    return reply.envelope(result, 'ai.invoke');
  });

  fastify.get('/models', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(models, 'ai.models');
  });

  fastify.get('/providers', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(providers, 'ai.providers');
  });

  fastify.post('/embeddings', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const body = request.body as any;
    if (!body?.input) {
      // @ts-ignore
      return reply.code(400).envelope({ error: 'input required' }, 'error.validation', 400);
    }
    const embeddings = {
      model: body.model ?? 'ortho-embed-1',
      data: [{ embedding: Array.from({ length: 8 }, () => Math.random()), index: 0 }],
      cycles: 8
    };
    // @ts-ignore
    return reply.envelope(embeddings, 'ai.embeddings');
  });

  fastify.get('/usage', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const usage = {
      tokensUsed: 1024,
      cyclesUsed: 2048,
      quota: 100000,
      period: 'monthly'
    };
    // @ts-ignore
    return reply.envelope(usage, 'ai.usage');
  });
}
