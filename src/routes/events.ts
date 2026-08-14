import { FastifyInstance } from 'fastify';
import { randomUUID } from 'node:crypto';

const EVENT_TYPES = [
  'device.connected',
  'device.disconnected',
  'fabric.transaction',
  'proof.verified',
  'proof.failed',
  'build.completed',
  'agent.started',
  'trace.completed',
  'security.prompt'
] as const;

export default async function eventRoutes(fastify: FastifyInstance) {
  fastify.get(
    '/stream',
    { preHandler: [(fastify as any).authenticate] },
    async (request, reply) => {
      // Establish SSE
      reply.raw.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no'
      });

      const send = (event: string, data: unknown) => {
        const envelope = {
          id: randomUUID(),
          type: event,
          timestamp: new Date().toISOString(),
          source: 'ortho32-api',
          correlation_id: (request.headers['x-correlation-id'] as string) || randomUUID(),
          data
        };
        reply.raw.write(`event: ${event}\n`);
        reply.raw.write(`data: ${JSON.stringify(envelope)}\n\n`);
      };

      // Initial hello
      send('connected', { message: 'sse connected', events: EVENT_TYPES });

      const interval = setInterval(() => {
        const ev = EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)];
        const dataByType: Record<string, unknown> = {
          'device.connected': { deviceId: 'ortho0' },
          'device.disconnected': { deviceId: 'sim0' },
          'fabric.transaction': { id: `txn-${Date.now()}`, cycles: 42 },
          'proof.verified': { proofId: randomUUID(), status: 'VERIFIED' },
          'proof.failed': { proofId: randomUUID(), status: 'FAILED' },
          'build.completed': { buildId: randomUUID(), status: 'success' },
          'agent.started': { agentId: 'verify' },
          'trace.completed': { traceId: randomUUID(), cycles: 256 },
          'security.prompt': { prompt: 'elevated_scope_request', scope: 'hardware.reset' }
        };
        send(ev, dataByType[ev] ?? {});
      }, 1000);

      // Heartbeat to keep connection alive
      const heartbeat = setInterval(() => {
        reply.raw.write(`: heartbeat ${Date.now()}\n\n`);
      }, 15000);

      request.raw.on('close', () => {
        clearInterval(interval);
        clearInterval(heartbeat);
        try {
          reply.raw.end();
        } catch {}
      });
    }
  );
}
