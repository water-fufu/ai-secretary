/**
 * 聊天状态管理
 * 管理当前会话的消息列表、流式输出状态、写入预览等
 */
import { create } from 'zustand'
import type { ChatSource, ChatMode } from '../types/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  mode?: ChatMode
  sources?: ChatSource[]
  isStreaming?: boolean
  hasConflict?: boolean
  conflictSummary?: string
  status?: string // 流式输出时的状态提示
}

interface ChatState {
  // 当前会话消息
  messages: ChatMessage[]
  // 是否正在流式输出
  isStreaming: boolean
  // 当前模式
  currentMode: ChatMode
  // 写入预览（待确认）
  writePreview: {
    preview: string
    pending: {
      formatted_content: string
      folder: string
      file_name: string
    }
  } | null

  // Actions
  addMessage: (msg: ChatMessage) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  appendToMessage: (id: string, content: string) => void
  setStreaming: (streaming: boolean) => void
  setMode: (mode: ChatMode) => void
  setWritePreview: (preview: any) => void
  clearWritePreview: () => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  currentMode: 'auto',
  writePreview: null,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m,
      ),
    })),

  appendToMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + content } : m,
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setMode: (mode) => set({ currentMode: mode }),

  setWritePreview: (preview) => set({ writePreview: preview }),

  clearWritePreview: () => set({ writePreview: null }),

  clearMessages: () => set({ messages: [], writePreview: null }),
}))
