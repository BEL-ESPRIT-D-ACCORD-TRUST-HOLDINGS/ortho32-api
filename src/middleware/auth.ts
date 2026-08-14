import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';

export interface CapabilityTokenPayload {
  sub: string;
  scopes: string[];
  iat: number;
  exp: number;
}

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
    authorize: (requiredScope: string) => (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: CapabilityTokenPayload;
    user: CapabilityTokenPayload;
  }
}

const ELEVATED_SCOPES = ['hardware.reset', 'marketplace.install'] as const;

export default async function authPlugin(fastify: FastifyInstance) {
  fastify.decorate('authenticate', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      await request.jwtVerify();
    } catch (err) {
      return reply.code(401).envelope(
        { error: 'unauthorized', message: (err as Error).message },
        'error.unauthorized',
        401
      );
    }
  });

  fastify.decorate('authorize', (requiredScope: string) => {
    return async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        await request.jwtVerify();
      } catch (err) {
        return reply.code(401).envelope(
          { error: 'unauthorized', message: (err as Error).message },
          'error.unauthorized',
          401
        );
      }
      const user = request.user as CapabilityTokenPayload;
      const scopes: string[] = user.scopes ?? [];
      if (!scopes.includes(requiredScope)) {
        return reply.code(403).envelope(
          {
            error: 'forbidden',
            message: `missing required scope: ${requiredScope}`,
            requiredScope,
            heldScopes: scopes
          },
          'error.forbidden',
          403
        );
      }
    };
  });
}

export const DEFAULT_SCOPES = [
  'devices.read',
  'devices.connect',
  'fabric.read',
  'fabric.commands',
  'tensor.jobs',
  'proofs.verify',
  'proofs.read',
  'builds.read',
  'builds.write',
  'traces.read',
  'traces.write',
  'agents.read',
  'agents.tasks',
  'apps.read',
  'apps.open',
  'workspaces.read',
  'workspaces.open',
  'events.stream',
  'ai.converse',
  'ai.invoke',
  'ai.models',
  'marketplace.read'
];

export { ELEVATED_SCOPES };
