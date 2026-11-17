// Backend DTOs mirroring FastAPI models

export interface ConnectPayload {
  dialect: 'postgresql' | 'mysql' | 'sqlite' | 'oracle' | 'mssql';
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database?: string;
  file_path?: string;
}

export interface Capabilities {
  readOnly: boolean;
  supportsTransactions: boolean;
  supportsSchemas: boolean;
}

export interface ConnectResponse {
  connection_id: string;
  databases: string[];
  default_database: string | null;
  capabilities: Capabilities;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  foreign_key_ref?: {
    table: string;
    column: string;
  };
}

export interface TableInfo {
  name: string;
  schema: string;
  columns: ColumnInfo[];
  approx_row_count?: number;
}

export interface SchemaInfo {
  name: string;
  tables: TableInfo[];
}

export interface DatabaseInfo {
  name: string;
  schemas: SchemaInfo[];
}

export interface SchemasResponse {
  connection_id: string;
  databases: DatabaseInfo[];
}

export interface TableDetailRequest {
  tables: string[];
}

export interface VisualNode {
  id: string;
  label: string;
  type?: string;
  columns?: Array<{
    name: string;
    type: string;
    is_primary_key?: boolean;
    is_foreign_key?: boolean;
    ref_table?: string | null;
    ref_column?: string | null;
  }>;
}

export interface VisualEdge {
  source: string;
  target: string;
  label?: string;
  source_column?: string | null;
  target_column?: string | null;
  cardinality?: string | null;
}

export interface VisualGraph {
  nodes: VisualNode[];
  edges: VisualEdge[];
}

export interface VisualizePayload {
  tables: string[];
  schema: string;
}

export interface NLQRunPayload {
  user_query: string;
  database?: string;
  schema?: string;
  table_scope?: string[];
  allow_modification?: boolean;
  return_sql_only?: boolean;
  confirm_execution?: boolean;
  model?: string;
}

export interface NLQRunResult {
  sql: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  truncated: boolean;
  warnings: string[];
  elapsed_ms: number;
  requires_confirmation?: boolean;
  confirmation_reason?: string | null;
  execution_skipped?: boolean;
  clarification_needed?: boolean;
  clarification_message?: string | null;
  generated_by?: string | null;
}

export interface NLQExplainResult {
  sql: string;
  parameters?: Record<string, any>;
  reasoning: string;
  is_read_only: boolean;
  limit_applied: boolean;
  confidence: number;
  generated_by?: string | null;
}

export interface HistoryItem {
  id: string;
  timestamp: string;
  user_query: string;
  sql: string;
  row_count?: number;
  elapsed_ms?: number;
  warnings?: string[];
  error?: string;
}

export interface ModelTag {
  name: string;
  is_default?: boolean;
  is_finetuned?: boolean;
}

export interface ModelsResponse {
  models: ModelTag[];
}

export interface ExportCSVPayload {
  sql: string;
  filename?: string;
}

export interface SafeModeResponse {
  enabled: boolean;
}

// Auth
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  username: string;
  email?: string | null;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
  last_login?: string | null;
}

// History (account-level)
export interface AccountHistoryItem {
  id: string;
  user_query: string;
  sql: string;
  database?: string | null;
  schema?: string | null;
  table_scope?: string[] | null;
  is_read_only: boolean;
  requires_confirmation: boolean;
  execution_skipped: boolean;
  row_count: number;
  elapsed_ms?: number | null;
  warnings: string[];
  status: string;
  error?: string | null;
  created_at: string;
}

export interface AccountHistoryResponse {
  items: AccountHistoryItem[];
  total: number;
}
