/**
 * API 类型定义
 * 与后端 Pydantic schemas 对应
 */

// ===== 通用 =====
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// ===== 聊天 =====
export type ChatMode = 'auto' | 'qa' | 'plan' | 'write' | 'claude'

export interface ChatRequest {
  message: string
  mode: ChatMode
  conversation_id?: number
}

export interface ChatSource {
  folder: string
  file_name: string
  section?: string
  timestamp?: string
}

/** SSE 事件类型 */
export type SSEEventType = 'status' | 'sources' | 'conflict' | 'token' | 'done' | 'error'

export interface SSEEvent {
  event: SSEEventType
  data: any
}

export interface StatusEvent {
  stage: string
  message: string
}

export interface SourcesEvent {
  count: number
  sources: ChatSource[]
}

export interface ConflictEvent {
  has_conflict: boolean
  summary: string
  newest: string
}

export interface TokenEvent {
  content: string
}

export interface DoneEvent {
  answer: string
  sources: ChatSource[]
  tokens_used: number
  latency_ms: number
  has_conflict?: boolean
  conflict_summary?: string
}

export interface ErrorEvent {
  code: string
  message: string
}

// ===== 写入 =====
export interface WritePreviewRequest {
  content: string
}

export interface WritePreviewResponse {
  preview: string
  pending: {
    formatted_content: string
    folder: string
    file_name: string
    is_new_file: boolean
  }
}

export interface WriteConfirmRequest {
  formatted_content: string
  folder: string
  file_name: string
}

export interface WriteConfirmResponse {
  success: boolean
  message: string
  folder: string
  file_name: string
  note_id: number
}

// ===== 笔记 =====
export interface Note {
  id: number
  folder: string
  file_name: string
  title?: string
  content: string
  source: string
  is_archived: number
  created_at: string
  updated_at: string
}

export interface NoteListResponse {
  total: number
  page: number
  page_size: number
  items: Note[]
}

// ===== 知识库 =====
export interface VaultStats {
  folder_count: number
  folders: string[]
  file_count: number
  chunk_count: number
  vector_indexed: number
  last_update: string | null
}

// ===== 会话 =====
export interface Conversation {
  id: number
  title: string
  mode: ChatMode
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  mode?: ChatMode
  sources?: ChatSource[]
  has_conflict?: number
  conflict_summary?: string
  created_at: string
}

// ===== 健康检查 =====
export interface HealthResponse {
  status: string
  version: string
  database: string
  redis: string
}
