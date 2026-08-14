import { FastifyInstance } from 'fastify';
import { FabricCommandSchema } from '../schemas/index.js';

const topology = {
  nodes: [
    { id: 'fabric-0', type: 'switch', links: ['ortho0', 'sim0'] },
    { id: 'ortho0', type: 'device', links: ['fabric-0'] },
    { id: 'sim0', type: 'device', links: ['fabric-0'] }
  ],
  links: [
    { from: 'fabric-0', to: 'ortho0', bandwidth: 100 },
    { from: 'fabric-0', to: 'sim0', bandwidth: 10 }
  ]
};

const transactions = [
  { id: 'txn-1', source: 'host', target: 'ortho0', cycles: 42, status: 'completed' as const },
  { id: 'txn-2', source: 'ortho0', target: 'host', cycles: 18, status: 'pending' as const }
];

export default async function fabricRoutes(fastify: FastifyInstance) {
  fastify.get('/topology', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(topology, 'fabric.topology');
  });

  fastify.get('/status', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const status = {
      state: 'online' as const,
      activeTransactions: transactions.filter((t) => t.status === 'pending').length,
      cycle: 1024,
      uptimeCycles: 987654
    };
    // @ts-ignore
    return reply.envelope(status, 'fabric.status');
  });

  fastify.get('/transactions', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // @ts-ignore
    return reply.envelope(transactions, 'fabric.transactions');
  });

  fastify.post('/commands', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = FabricCommandSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const cmd = parsed.data;
    const result = {
      id: `cmd-${Date.now()}`,
      command: cmd.command,
      status: 'accepted',
      cycles: 4
    };
    // @ts-ignore
    return reply.envelope(result, 'fabric.command.accepted');
  });
}
