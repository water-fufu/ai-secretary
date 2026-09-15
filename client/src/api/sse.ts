/**
 * SSE 流式接收
 * 使用 fetch + ReadableStream 实现（支持 POST 请求体）
 */
import type { SSEEvent, SSEEventType } from '../types/api'

/**
 * 解析 SSE 响应流
 * @param response fetch Response 对象
 * @param onEvent 事件回调
 */
export async function parseSSEStream(
  response: Response,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE 事件以 \n\n 分隔
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const eventStr of events) {
      if (!eventStr.trim()) continue

      const event = parseSSEEvent(eventStr)
      if (event) {
        onEvent(event)
      }
    }
  }
}

/**
 * 解析单个 SSE 事件
 * 格式：
 * event: xxx
 * data: {...}
 */
function parseSSEEvent(eventStr: string): SSEEvent | null {
  const lines = eventStr.split('\n')
  let eventType: SSEEventType = 'token'
  let dataStr = ''

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim() as SSEEventType
    } else if (line.startsWith('data:')) {
      dataStr += line.slice(5).trim()
    }
  }

  if (!dataStr) return null

  try {
    return {
      event: eventType,
      data: JSON.parse(dataStr),
    }
  } catch {
    return {
      event: eventType,
      data: { content: dataStr },
    }
  }
}

/**
 * 发送 SSE 流式请求
 * @param url 请求路径
 * @param body 请求体
 * @param onEvent 事件回调
 */
export async function postSSE(
  url: string,
  body: any,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const baseURL = await getBaseURL()
  const response = await fetch(`${baseURL}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  await parseSSEStream(response, onEvent)
}

// 获取 baseURL（与 client.ts 保持一致）
async function getBaseURL(): Promise<string> {
  try {
    const config = await window.mishu.getConfig()
    return config.apiBaseUrl || ''
  } catch {
    return ''
  }
}
