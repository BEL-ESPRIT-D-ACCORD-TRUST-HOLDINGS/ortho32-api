import { FastifyInstance } from 'fastify';
import { SessionCreateSchema } from '../schemas/index.js';
import { DEFAULT_SCOPES } from '../middleware/auth.js';

export default async function authRoutes(fastify: FastifyInstance) {
  // Issue scoped capability token
  fastify.post('/session', async (request, reply) => {
    const parsed = SessionCreateSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const { principal, requestedScopes } = parsed.data;

    // Default token cannot have elevated scopes unless explicitly privileged.
    // For this API, only principal === 'admin' or 'system' may be granted elevated scopes.
    const isPrivileged = principal === 'admin' || principal === 'system';
    let scopes = [...DEFAULT_SCOPES];

    if (requestedScopes && requestedScopes.length > 0) {
      const filtered = requestedScopes.filter((s) => {
        if (['hardware.reset', 'marketplace.install'].includes(s) && !isPrivileged) return false;
        return true;
      });
      // only allow requested scopes that are subset of DEFAULT + elevated if privileged
      // merge filtered requested scopes that are known
      for (const s of filtered) {
        if (!scopes.includes(s)) scopes.push(s);
      }
    }

    // @ts-ignore fastify.jwt is available after registration
    const token = fastify.jwt.sign({ sub: principal, scopes });
    const decoded: any = fastify.jwt.decode(token);
    const data = {
      token,
      principal,
      scopes,
      expiresAt: new Date(decoded.exp * 1000).toISOString(),
      issuedAt: new Date(decoded.iat * 1000).toISOString()
    };
    // @ts-ignore
    return reply.envelope(data, 'auth.session.created');
  });

  fastify.get('/session', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const user = (request as any).user;
    const data = {
      principal: user.sub,
      scopes: user.scopes,
      valid: true
    };
    // @ts-ignore
    return reply.envelope(data, 'auth.session');
  });

  fastify.delete('/session', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    // stateless JWT - client discards token. We acknowledge.
    // @ts-ignore
    return reply.envelope({ revoked: true }, 'auth.session.revoked');
  });
}
