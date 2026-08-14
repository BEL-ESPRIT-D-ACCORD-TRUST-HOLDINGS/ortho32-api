import { z } from 'zod';

// ---------------------------------------------------------------------------
// Envelope
// ---------------------------------------------------------------------------
export const EnvelopeSchema = z.object({
  id: z.string().uuid().describe('unique envelope id'),
  type: z.string().describe('event/response type dot notation'),
  timestamp: z.string().datetime().describe('ISO8601 timestamp'),
  source: z.string().describe('originating service, always ortho32-api'),
  correlation_id: z.string().describe('request correlation id for tracing'),
  data: z.unknown()
});

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------
// cycles: architectural cycle count, integer, NEVER wall-clock ms or float
export const CyclesSchema = z
  .number()
  .int()
  .nonnegative()
  .describe('architectural cycles - integer count of hardware/fabric cycles. NEVER wall-clock time (ms) and NEVER float.');

export const CycleRecordSchema = z.object({
  cycleNumber: z.number().int().nonnegative().describe('monotonic architectural cycle index, integer'),
  timestamp: z.string().datetime(),
  signals: z.record(z.unknown()).optional(),
  fabricState: z.string().optional()
});

// VerificationStatus: exactly 7 values, semantically disjoint, never interchangeable
export const VerificationStatusSchema = z.enum([
  'VERIFIED',
  'CROSS_VERIFIED',
  'TESTED',
  'OBSERVED',
  'ASSUMED',
  'UNVERIFIED',
  'FAILED'
]).describe('Proof verification status - 7 disjoint values. NEVER interchangeable. VERIFIED != CROSS_VERIFIED etc.');

// ---------------------------------------------------------------------------
// Public domain entities - NEVER expose BAR0 / Win32 HANDLE / raw FPGA pointer
// ---------------------------------------------------------------------------
export const DeviceSchema = z.object({
  id: z.string().describe('device identifier, e.g. ortho0'),
  name: z.string(),
  status: z.enum(['connected', 'disconnected', 'error', 'resetting']),
  kind: z.enum(['ortho32', 'simulated', 'remote']),
  fabricId: z.string().optional(),
  capabilities: z.array(z.string()).optional(),
  lastSeen: z.string().datetime().optional()
  // NOTE: no bar0, no handle, no fpgaPointer
});

export const FabricTopologySchema = z.object({
  nodes: z.array(z.object({ id: z.string(), type: z.string(), links: z.array(z.string()) })),
  links: z.array(z.object({ from: z.string(), to: z.string(), bandwidth: z.number() }))
});

export const FabricStatusSchema = z.object({
  state: z.enum(['online', 'offline', 'degraded']),
  activeTransactions: z.number().int().nonnegative(),
  cycle: CyclesSchema,
  uptimeCycles: CyclesSchema
});

export const FabricTransactionSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  cycles: CyclesSchema,
  status: z.enum(['pending', 'completed', 'failed'])
});

export const TensorJobSchema = z.object({
  id: z.string(),
  status: z.enum(['queued', 'running', 'completed', 'failed']),
  model: z.string().optional(),
  inputShape: z.array(z.number()).optional(),
  cycles: CyclesSchema.describe('execution cost in architectural cycles (int)'),
  createdAt: z.string().datetime(),
  completedAt: z.string().datetime().optional(),
  result: z.unknown().optional()
});

export const TensorJobCreateSchema = z.object({
  model: z.string(),
  input: z.unknown().optional(),
  inputShape: z.array(z.number()).optional(),
  options: z.record(z.unknown()).optional()
});

export const ProofSchema = z.object({
  id: z.string(),
  theorem: z.string(),
  status: VerificationStatusSchema,
  dependencies: z.array(z.string()).optional(),
  verifiedAt: z.string().datetime().optional(),
  details: z.string().optional()
});

export const ProofVerifyRequestSchema = z.object({
  theorem: z.string(),
  artifact: z.string().optional(),
  dependencies: z.array(z.string()).optional()
});

export const BuildSchema = z.object({
  id: z.string(),
  status: z.enum(['queued', 'building', 'success', 'failed']),
  target: z.string(),
  cycles: CyclesSchema.optional(),
  createdAt: z.string().datetime(),
  logs: z.array(z.string()).optional()
});

export const TraceSchema = z.object({
  id: z.string(),
  status: z.enum(['capturing', 'completed', 'failed']),
  cycles: CyclesSchema,
  records: z.array(CycleRecordSchema).optional(),
  createdAt: z.string().datetime()
});

export const TraceCaptureRequestSchema = z.object({
  deviceId: z.string().optional(),
  durationCycles: CyclesSchema.optional(),
  trigger: z.string().optional()
});

export const AgentSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum(['idle', 'running', 'error']),
  capabilities: z.array(z.string())
});

export const AgentTaskSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  type: z.string(),
  status: z.enum(['queued', 'running', 'completed', 'failed']),
  input: z.unknown().optional(),
  output: z.unknown().optional(),
  cycles: CyclesSchema.optional(),
  createdAt: z.string().datetime()
});

export const AppSchema = z.object({
  id: z.string().describe('app id e.g. org.ortho.ide'),
  name: z.string(),
  route: z.string().describe('ortho:// route for the app'),
  version: z.string().optional()
});

export const MarketplacePackageSchema = z.object({
  id: z.string(),
  name: z.string(),
  version: z.string(),
  description: z.string().optional(),
  author: z.string().optional(),
  installed: z.boolean().optional()
});

export const WorkspaceSchema = z.object({
  id: z.string(),
  name: z.string(),
  routes: z.array(z.string()).describe('ortho:// routes stored not UI objects'),
  current: z.boolean().optional()
});

export const AiConverseRequestSchema = z.object({
  model: z.string().optional(),
  messages: z.array(z.object({ role: z.enum(['user', 'assistant', 'system']), content: z.string() })),
  stream: z.boolean().optional()
});

export const AiInvokeRequestSchema = z.object({
  agentId: z.string().optional(),
  task: z.string(),
  input: z.unknown().optional()
});

// Auth
export const SessionCreateSchema = z.object({
  principal: z.string().describe('user or service principal'),
  credentials: z.string().optional(),
  // requestedScopes is ignored for elevated scopes unless caller is privileged
  requestedScopes: z.array(z.string()).optional()
});

// Fabric command
export const FabricCommandSchema = z.object({
  command: z.string(),
  target: z.string().optional(),
  payload: z.unknown().optional()
});
