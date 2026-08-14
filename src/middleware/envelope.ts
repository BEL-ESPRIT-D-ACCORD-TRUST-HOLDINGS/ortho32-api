import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { randomUUID } from 'node:crypto';

export interface Envelope<T = unknown> {
  id: string;
  type: string;
  timestamp: string;
  source: string;
  correlation_id: string;
  data: T;
}

export function buildEnvelope<T>(
  data: T,
  request: FastifyRequest,
  type?: string
): Envelope<T> {
  const correlationId =
    (request.headers['x-correlation-id'] as string) ||
    (request.headers['x-request-id'] as string) ||
    randomUUID();

  return {
    id: randomUUID(),
    type: type || `${request.method.toLowerCase()}.${request.url.replace(/\//g, '.').replace(/^\.+/, '')}`,
    timestamp: new Date().toISOString(),
    source: 'ortho32-api',
    correlation_id: correlationId,
    data
  };
}

declare module 'fastify' {
  interface FastifyReply {
    envelope: <T>(data: T, type?: string, statusCode?: number) => FastifyReply;
  }
}

export default async function envelopePlugin(fastify: FastifyInstance) {
  fastify.decorateReply('envelope', function <T>(
    this: FastifyReply,
    data: T,
    type?: string,
    statusCode: number = 200
  ) {
    const request = this.request as FastifyRequest;
    const envelope = buildEnvelope(data, request, type);
    // expose correlation id to client
    this.header('x-correlation-id', envelope.correlation_id);
    this.code(statusCode);
    return this.send(envelope);
  });

  // Ensure error responses are also enveloped
  fastify.setErrorHandler((error, request, reply) => {
    const status = error.statusCode ?? 500;
    const envelope = buildEnvelope(
      {
        error: error.message,
        code: error.code ?? 'internal_error'
      },
      request,
      'error'
    );
    reply.code(status).header('x-correlation-id', envelope.correlation_id).send(envelope);
  });
}
