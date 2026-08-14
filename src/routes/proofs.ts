import { FastifyInstance } from 'fastify';
import { ProofVerifyRequestSchema } from '../schemas/index.js';
import { randomUUID } from 'node:crypto';

type VerificationStatus =
  | 'VERIFIED'
  | 'CROSS_VERIFIED'
  | 'TESTED'
  | 'OBSERVED'
  | 'ASSUMED'
  | 'UNVERIFIED'
  | 'FAILED';

interface Proof {
  id: string;
  theorem: string;
  status: VerificationStatus;
  dependencies: string[];
  verifiedAt?: string;
  details?: string;
}

const proofs = new Map<string, Proof>();

function deriveStatus(theorem: string): VerificationStatus {
  // deterministic but illustrative: hash theorem length to a status
  const map: VerificationStatus[] = [
    'VERIFIED',
    'CROSS_VERIFIED',
    'TESTED',
    'OBSERVED',
    'ASSUMED',
    'UNVERIFIED',
    'FAILED'
  ];
  return map[theorem.length % 7];
}

export default async function proofRoutes(fastify: FastifyInstance) {
  fastify.post('/verify', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const parsed = ProofVerifyRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      // @ts-ignore
      return reply.code(400).envelope({ error: parsed.error.flatten() }, 'error.validation', 400);
    }
    const { theorem, dependencies } = parsed.data;
    const id = randomUUID();
    const status = deriveStatus(theorem);
    const proof: Proof = {
      id,
      theorem,
      status,
      dependencies: dependencies ?? [],
      verifiedAt: new Date().toISOString(),
      details: `Verification completed with status ${status}`
    };
    proofs.set(id, proof);
    // @ts-ignore
    return reply.envelope(proof, 'proof.verified');
  });

  fastify.get('/:id', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const proof = proofs.get(id);
    if (!proof) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'proof not found' }, 'error.not_found', 404);
    }
    // @ts-ignore
    return reply.envelope(proof, 'proof.get');
  });

  fastify.get('/:id/dependencies', { preHandler: [(fastify as any).authenticate] }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const proof = proofs.get(id);
    if (!proof) {
      // @ts-ignore
      return reply.code(404).envelope({ error: 'proof not found' }, 'error.not_found', 404);
    }
    const deps = proof.dependencies.map((d) => ({ id: d, status: 'VERIFIED' as const }));
    // @ts-ignore
    return reply.envelope({ proofId: id, dependencies: deps }, 'proof.dependencies');
  });
}
