export type EstadoLabel = string;

export interface Me {
  actor_id: string;
  is_demo: boolean;
  demo_mode: boolean;
}

export interface SourceListItem {
  id: number;
  provider: string;
  external_id: string | null;
  canonical_url: string | null;
  title: string | null;
  author: string | null;
  published_at: string | null;
  imported_at: string;
  language: string | null;
  status: string;
  status_label: EstadoLabel;
  demo: boolean;
  metadata: Record<string, unknown>;
}

export interface SourceContentInfo {
  id: number;
  content_type: string;
  content_type_label: string;
  is_verbatim: boolean;
  provider: string | null;
  model: string | null;
  coverage: number | null;
  confidence: string | null;
  extracted_at: string;
  char_count: number;
  segment_count: number;
}

export interface StoryRef {
  id: number;
  title: string;
  status: string;
  status_label: string;
}

export interface SourceDetail extends SourceListItem {
  contents: SourceContentInfo[];
  stories: StoryRef[];
}

export interface EvidenceItem {
  id: number;
  url: string | null;
  publisher: string | null;
  published_at: string | null;
  retrieved_at: string;
  excerpt_or_paraphrase: string | null;
  kind: string;
  confidence: string;
  demo: boolean;
}

export interface ClaimItem {
  id: number;
  statement: string;
  verification_status: string;
  verification_notes: string | null;
  evidence: EvidenceItem[];
}

export interface ScriptVersionItem {
  id: number;
  version: number;
  content: string;
  target_duration_s: number | null;
  language: string;
  author_type: string;
  created_at: string;
  content_hash: string;
}

export interface PossibleDuplicate {
  story_id: number;
  title: string;
  status_label: string;
  reason: string;
  similarity: number;
}

export interface StoryListItem {
  id: number;
  topic_key: string;
  title: string;
  summary: string | null;
  status: string;
  status_label: string;
  editorial_score: number | null;
  score_breakdown: Record<string, unknown>;
  is_opinion: boolean;
  original_event_date: string | null;
  created_at: string;
  source_count?: number;
  unverified_claims?: number;
  possible_duplicates?: PossibleDuplicate[];
}

export interface StoryDetail extends StoryListItem {
  sources: {
    source_id: number;
    provider: string;
    title: string | null;
    canonical_url: string | null;
    published_at: string | null;
    status_label: string;
    relevance: string | null;
  }[];
  claims: ClaimItem[];
  script_versions: ScriptVersionItem[];
  active_approval: {
    script_version_id: number;
    approved_at: string;
    actor: string;
    content_hash: string;
  } | null;
  pending_approval_flag: boolean;
}

export interface StoryboardScene {
  message: string;
  seconds: number;
  visual: string;
  data_source: string | null;
  image_prompt: string;
  overlay_text: string | null;
}

export interface Storyboard {
  story_id: number;
  script_version: number;
  approved: boolean;
  scenes: StoryboardScene[];
  note: string;
}

export interface BatchStory {
  position: number;
  story_id: number;
  title: string;
  status: string;
  status_label: string;
  approved: boolean;
  script_version: number | null;
  pending_reason: string | null;
}

export interface BatchDetail {
  id: number;
  name: string;
  target_size: number;
  status: string;
  stories: BatchStory[];
  ready_count: number;
  pending_count: number;
  packages?: { id: number; version: number; sha256: string; state: string; created_at: string }[];
}

export interface JobInfo {
  id: number;
  type: string;
  status: string;
  status_label: string;
  attempt?: number;
  progress?: string | null;
  error?: string | null;
  created_at?: string;
}

export interface ProviderStatus {
  key: string;
  name: string;
  configured: boolean;
  state: string;
  note: string;
}

export interface UsageInfo {
  today_calls: number;
  today_blocked: number;
  today_spent_eur: number;
  by_provider: Record<string, number>;
  budget: { paid_services_enabled: boolean; daily_limit_eur: number };
}
