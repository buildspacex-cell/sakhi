import { Pool } from "pg";
import crypto from "node:crypto";
import type {
  ShortTermInteraction,
  EpisodicRecord,
  SemanticTrait,
  PreferenceRecord,
  IdentityEdge
} from "@sakhi/contracts";
import type { MemoryService } from "./types";

const CREATE_TABLES_SQL = `
CREATE TABLE IF NOT EXISTS memory_short_term (
  id uuid PRIMARY KEY,
  user_id text NOT NULL,
  record jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT (now() + INTERVAL '14 days')
);
CREATE INDEX IF NOT EXISTS idx_memory_short_term_user ON memory_short_term (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS memory_episodic (
  id uuid PRIMARY KEY,
  user_id text NOT NULL,
  record jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memory_episodic_user ON memory_episodic (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS memory_semantic_traits (
  user_id text NOT NULL,
  trait_key text NOT NULL,
  record jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, trait_key)
);

CREATE TABLE IF NOT EXISTS memory_preferences (
  user_id text NOT NULL,
  pref_scope text NOT NULL,
  pref_key text NOT NULL,
  record jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, pref_scope, pref_key)
);

CREATE TABLE IF NOT EXISTS memory_identity_edges (
  user_id text NOT NULL,
  edge_from text NOT NULL,
  edge_to text NOT NULL,
  relationship text NOT NULL,
  record jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, edge_from, edge_to, relationship)
);
`;

export type PostgresMemoryServiceConfig = {
  connectionString: string;
};

export class PostgresMemoryService implements MemoryService {
  private readonly pool: Pool;
  private readonly ready: Promise<void>;

  constructor(config: PostgresMemoryServiceConfig) {
    this.pool = new Pool({ connectionString: config.connectionString });
    this.ready = this.initialise();
  }

  private async initialise(): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query(CREATE_TABLES_SQL);
    } finally {
      client.release();
    }
  }

  private async ensureReady() {
    await this.ready;
  }

  async appendShortTerm(userId: string, record: ShortTermInteraction): Promise<void> {
    await this.ensureReady();
    const payload = { ...record, id: record.id ?? crypto.randomUUID() };
    await this.pool.query(
      `INSERT INTO memory_short_term (id, user_id, record) VALUES ($1, $2, $3)`,
      [payload.id, userId, JSON.stringify(payload)]
    );
  }

  async getShortTerm(userId: string, limit: number): Promise<ShortTermInteraction[]> {
    await this.ensureReady();
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_short_term WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2`,
      [userId, limit]
    );
    return rows.map((row) => row.record as ShortTermInteraction);
  }

  async appendEpisodic(userId: string, record: EpisodicRecord): Promise<void> {
    await this.ensureReady();
    const payload = { ...record, id: record.id ?? crypto.randomUUID() };
    await this.pool.query(
      `INSERT INTO memory_episodic (id, user_id, record) VALUES ($1, $2, $3)`,
      [payload.id, userId, JSON.stringify(payload)]
    );
  }

  async searchEpisodic(userId: string, query: string, limit: number): Promise<EpisodicRecord[]> {
    await this.ensureReady();
    const like = `%${query}%`;
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_episodic
       WHERE user_id = $1 AND (record->>'text') ILIKE $2
       ORDER BY created_at DESC
       LIMIT $3`,
      [userId, like, limit]
    );
    return rows.map((row) => row.record as EpisodicRecord);
  }

  async upsertSemanticTrait(userId: string, trait: SemanticTrait): Promise<void> {
    await this.ensureReady();
    await this.pool.query(
      `INSERT INTO memory_semantic_traits (user_id, trait_key, record, updated_at)
       VALUES ($1, $2, $3, now())
       ON CONFLICT (user_id, trait_key) DO UPDATE SET record = EXCLUDED.record, updated_at = now()`,
      [userId, trait.key, JSON.stringify(trait)]
    );
  }

  async getSemanticTrait(userId: string, key: string): Promise<SemanticTrait | null> {
    await this.ensureReady();
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_semantic_traits WHERE user_id = $1 AND trait_key = $2`,
      [userId, key]
    );
    if (!rows.length) return null;
    return rows[0].record as SemanticTrait;
  }

  async listSemanticTraits(userId: string): Promise<SemanticTrait[]> {
    await this.ensureReady();
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_semantic_traits WHERE user_id = $1`,
      [userId]
    );
    return rows.map((row) => row.record as SemanticTrait);
  }

  async removeSemanticTrait(userId: string, key: string): Promise<void> {
    await this.ensureReady();
    await this.pool.query(
      `DELETE FROM memory_semantic_traits WHERE user_id = $1 AND trait_key = $2`,
      [userId, key]
    );
  }

  async upsertPreference(userId: string, pref: PreferenceRecord): Promise<void> {
    await this.ensureReady();
    const key = pref.key ?? "default";
    const scope = pref.scope ?? "other";
    await this.pool.query(
      `INSERT INTO memory_preferences (user_id, pref_scope, pref_key, record, updated_at)
       VALUES ($1, $2, $3, $4, now())
       ON CONFLICT (user_id, pref_scope, pref_key) DO UPDATE SET record = EXCLUDED.record, updated_at = now()`,
      [userId, scope, key, JSON.stringify(pref)]
    );
  }

  async listPreferences(userId: string): Promise<PreferenceRecord[]> {
    await this.ensureReady();
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_preferences WHERE user_id = $1`,
      [userId]
    );
    return rows.map((row) => row.record as PreferenceRecord);
  }

  async upsertIdentityEdge(userId: string, edge: IdentityEdge): Promise<void> {
    await this.ensureReady();
    await this.pool.query(
      `INSERT INTO memory_identity_edges (user_id, edge_from, edge_to, relationship, record, updated_at)
       VALUES ($1, $2, $3, $4, $5, now())
       ON CONFLICT (user_id, edge_from, edge_to, relationship)
       DO UPDATE SET record = EXCLUDED.record, updated_at = now()`,
      [userId, edge.from, edge.to, edge.relationship, JSON.stringify(edge)]
    );
  }

  async listIdentityEdges(userId: string): Promise<IdentityEdge[]> {
    await this.ensureReady();
    const { rows } = await this.pool.query(
      `SELECT record FROM memory_identity_edges WHERE user_id = $1`,
      [userId]
    );
    return rows.map((row) => row.record as IdentityEdge);
  }
}
