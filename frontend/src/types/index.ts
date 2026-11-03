/* TypeScript interfaces matching backend Pydantic schemas */

// ---- Document ----
export interface Document {
  document_id: string;
  filename: string;
  file_path: string;
  doc_type: string;
  doc_title: string | null;
  revision: string | null;
  source_system: string | null;
  trust_level: string;
  extraction_status: string;
  file_size_bytes: number;
  chunk_count: number;
  fact_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Entity Alias ----
export interface EntityAlias {
  alias_id: string;
  entity_id: string;
  alias_name: string;
  resolution_method: string;
  confidence_score: number;
  created_at: string;
}

// ---- Entity ----
export interface Entity {
  entity_id: string;
  canonical_name: string;
  entity_type: string;
  description: string | null;
  system_context: string | null;
  meta_info: Record<string, any>;
  created_at: string;
  updated_at: string;
  aliases: EntityAlias[];
}

// ---- Evidence ----
export interface Evidence {
  evidence_id: string;
  fact_id: string;
  document_id: string;
  snippet: string;
  chunk_id: string | null;
  page_number: number | null;
  confidence_score: number;
  extraction_method: string;
  meta_info: Record<string, any>;
  created_at: string;
}

// ---- Fact ----
export interface Fact {
  fact_id: string;
  entity_id: string;
  predicate: string;
  value: string;
  unit: string | null;
  data_type: string;
  numeric_value: number | null;
  tolerance_min: number | null;
  tolerance_max: number | null;
  verification_status: string;
  confidence_score: number;
  is_current: boolean;
  meta_info: Record<string, any>;
  created_at: string;
  updated_at: string;
  evidence: Evidence[];
}

// ---- Conflict ----
export interface Conflict {
  conflict_id: string;
  predicate: string;
  description: string;
  conflict_type: string;
  status: string;
  resolution_notes: string | null;
  resolution_method: string | null;
  resolved_by: string | null;
  meta_info: Record<string, any>;
  created_at: string;
  resolved_at: string | null;
  facts: Fact[];
}

// ---- Query/Answer ----
export interface Claim {
  claim_id: string;
  entity_name: string;
  predicate: string;
  value: string;
  unit: string | null;
  status: string;
  confidence: number;
  source_doc: string | null;
}

export interface EvidenceItem {
  evidence_id: string;
  fact_id: string | null;
  document_name: string | null;
  snippet: string;
  page_number: number | null;
  confidence_score: number;
  extraction_method: string;
}

export interface ConflictInfo {
  conflict_id: string;
  predicate: string;
  description: string;
  conflict_type: string;
  status: string;
  conflicting_values: string[];
  resolution_notes: string | null;
}

export interface QueryResponse {
  question: string;
  answer: string;
  confidence: number;
  claims: Claim[];
  evidence: EvidenceItem[];
  conflicts: ConflictInfo[];
  query_time_ms: number;
  status: string;
}

// ---- Ingestion ----
export interface IngestionStatus {
  status: string;
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  total_chunks: number;
  total_facts: number;
  total_conflicts: number;
  active_jobs: number;
  last_ingested_at: string | null;
}

export interface IngestionReport {
  job_id: string;
  status: string;
  documents_processed: number;
  documents_failed: number;
  total_chunks_created: number;
  total_facts_extracted: number;
  total_conflicts_identified: number;
  processing_time_seconds: number;
  details: Record<string, any>[];
  errors: string[];
}

// ---- Evaluation ----
export interface QuestionResult {
  question_id: string;
  question: string;
  expected_answer: string | null;
  generated_answer: string;
  accuracy_score: number;
  evidence_grounding_score: number;
  latency_ms: number;
  claims_count: number;
  conflicts_detected: number;
  passed: boolean;
}

export interface EvaluationMetrics {
  total_questions: number;
  passed_questions: number;
  accuracy: number;
  evidence_grounding_ratio: number;
  conflict_detection_rate: number;
  avg_latency_ms: number;
}

export interface EvaluationResult {
  run_id: string;
  status: string;
  timestamp: string;
  metrics: EvaluationMetrics;
  results: QuestionResult[];
}

// ---- Chat ----
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
  loading?: boolean;
}
