/**
 * 聊天相关 API
 */
import apiClient from './client'
import { postSSE } from './sse'
import type {
  ChatRequest,
  SSEEvent,
  WritePreviewRequest,
  WritePreviewResponse,
  WriteConfirmRequest,
  WriteConfirmResponse,
} from '../types/api'

/**
 * 发送聊天消息（SSE 流式）
 * @param request 聊天请求
 * @param onEvent SSE 事件回调
 */
export async function sendChat(
  request: ChatRequest,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  await postSSE('/api/v1/chat', request, onEvent)
}

/**
 * 写入预览
 */
export async function writePreview(
  content: string,
): Promise<WritePreviewResponse> {
  const body: WritePreviewRequest = { content }
  const { data } = await apiClient.post('/api/v1/chat/write/preview', body)
  return data
}

/**
 * 确认写入
 */
export async function writeConfirm(
  request: WriteConfirmRequest,
): Promise<WriteConfirmResponse> {
  const { data } = await apiClient.post('/api/v1/chat/write/confirm', request)
  return data
}
