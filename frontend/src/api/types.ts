/** Shared API types (mirror backend schemas). */

export interface User {
  id: number
  email: string
  display_name: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Agent {
  id: number
  user_id: number
  name: string
  description: string
  persona_prompt: string | null
  welcome_message: string
  avatar_emoji: string
  avatar_url: string | null
  avatar_kind: 'photo' | 'template'
  chat_theme: string
  show_thinking: boolean
  show_tools: boolean
  public_token: string
  created_at: string
  updated_at: string
}

export interface Source {
  id: number
  agent_id: number
  url: string
  kind: 'url' | 'pdf' | 'text'
  file_name: string | null
  file_size: number | null
  status: SourceStatus
  title: string | null
  error: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export type SourceStatus = 'pending' | 'fetching' | 'indexing' | 'ready' | 'failed'

export const RUNNING_SOURCE_STATUSES: SourceStatus[] = ['pending', 'fetching', 'indexing']

export interface EmbedResponse {
  html: string
  agent_id: number
  public_token: string
}

export interface ChatMessage {
  type: 'human' | 'ai'
  content: string
  tool_calls?: { id: string; name: string; args: Record<string, unknown> }[]
}

export interface SourceCitation {
  url: string
  title: string
}

// --- usage (dashboard tab) ---
export type UsageChannel = 'preview' | 'widget'
export type UsageStatus = 'completed' | 'failed' | 'cancelled'

export interface UsageLog {
  id: number
  channel: UsageChannel
  thread_id: string
  model: string | null
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost: number | null
  country: string | null
  status: UsageStatus
  created_at: string
  // URL of the page where the widget was embedded ("from where it was called").
  page_url?: string | null
  // Filled only by admin (platform-wide) queries.
  agent_id?: number | null
  agent_name?: string | null
}

export interface UsagePoint {
  date: string
  requests: number
  input_tokens: number
  output_tokens: number
}

export interface UsageCountry {
  country: string
  requests: number
}

export interface UsageSummary {
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  series: UsagePoint[]
  countries: UsageCountry[]
}

export interface UsageResponse {
  summary: UsageSummary
  items: UsageLog[]
  total: number
  page: number
  page_size: number
  pages: number
}

// --- admin (read-only platform monitoring) ---
export interface AdminTokenResponse {
  access_token: string
  token_type: string
  email: string
}

export interface AdminUserRow {
  id: number
  email: string
  display_name: string
  created_at: string
  agent_count: number
  total_requests: number
  total_tokens: number
  last_active: string | null
}

export interface AdminUsersResponse {
  items: AdminUserRow[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AdminAgentRow {
  id: number
  name: string
  description: string
  avatar_emoji: string
  avatar_url: string | null
  chat_theme: string
  created_at: string
  source_count: number
  ready_sources: number
  total_requests: number
  total_tokens: number
  last_active: string | null
}

export interface AdminUserDetail {
  user: AdminUserRow
  agents: AdminAgentRow[]
}

export interface AdminAgentDetail {
  agent: Agent
  user: AdminUserRow
}

export interface AdminStats {
  total_users: number
  total_agents: number
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  series: UsagePoint[]
}
