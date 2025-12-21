CREATE TABLE IF NOT EXISTS ay_nodes (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  attrs JSONB DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS ay_nodes_kind_name_idx
ON ay_nodes(kind, name);

CREATE TABLE IF NOT EXISTS ay_edges (
  src BIGINT REFERENCES ay_nodes(id) ON DELETE CASCADE,
  dst BIGINT REFERENCES ay_nodes(id) ON DELETE CASCADE,
  rel TEXT NOT NULL,
  weight NUMERIC DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS ay_edges_src_dst_idx
ON ay_edges(src, dst);
