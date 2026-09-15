/**
 * 聊天输入框
 * 支持发送消息、写入预览确认
 */
import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useConfigStore } from '../../store/configStore'
import { sendChat, writePreview as fetchWritePreview, writeConfirm } from '../../api/chat'
import type { SSEEvent } from '../../types/api'
import { ModeSelector } from './ModeSelector'

export function InputBox() {
  const [input, setInput] = useState('')
  const {
    messages,
    isStreaming,
    currentMode,
    writePreview,
    addMessage,
    updateMessage,
    appendToMessage,
    setStreaming,
    setWritePreview,
    clearWritePreview,
  } = useChatStore()
  const { config } = useConfigStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  // 检查 API 是否配置
  const isApiConfigured = config?.apiBaseUrl && config.apiBaseUrl.length > 0

  /**
   * 发送消息
   */
  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    // 检查 API 配置
    if (!isApiConfigured) {
      addMessage({
        id: `sys-${Date.now()}`,
        role: 'system',
        content: '⚠ 请先在设置中配置云端 API 地址',
      })
      return
    }

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user' as const,
      content: input.trim(),
      mode: currentMode,
    }
    addMessage(userMsg)

    // 写入模式：先预览
    if (currentMode === 'write') {
      try {
        const result = await fetchWritePreview(input.trim())
        setWritePreview(result)
        addMessage({
          id: `preview-${Date.now()}`,
          role: 'assistant',
          content: result.preview,
        })
      } catch (e) {
        addMessage({
          id: `err-${Date.now()}`,
          role: 'system',
          content: `❌ 写入预览失败：${(e as Error).message}`,
        })
      }
      setInput('')
      return
    }

    // 其他模式：SSE 流式输出
    const assistantId = `assistant-${Date.now()}`
    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      status: '正在思考...',
    })
    setStreaming(true)
    setInput('')

    try {
      await sendChat(
        { message: userMsg.content, mode: currentMode },
        (event: SSEEvent) => {
          switch (event.event) {
            case 'status':
              updateMessage(assistantId, { status: event.data.message })
              break
            case 'sources':
              updateMessage(assistantId, {
                sources: event.data.sources,
                status: undefined,
              })
              break
            case 'conflict':
              updateMessage(assistantId, {
                hasConflict: true,
                conflictSummary: event.data.summary,
              })
              break
            case 'token':
              appendToMessage(assistantId, event.data.content)
              break
            case 'done':
              updateMessage(assistantId, {
                isStreaming: false,
                status: undefined,
                content: event.data.answer,
                sources: event.data.sources,
                hasConflict: event.data.has_conflict,
                conflictSummary: event.data.conflict_summary,
              })
              break
            case 'error':
              updateMessage(assistantId, {
                isStreaming: false,
                status: undefined,
                content: `❌ ${event.data.message}`,
              })
              break
          }
        },
      )
    } catch (e) {
      updateMessage(assistantId, {
        isStreaming: false,
        status: undefined,
        content: `❌ 请求失败：${(e as Error).message}`,
      })
    } finally {
      setStreaming(false)
    }
  }

  /**
   * 确认写入
   */
  const handleConfirmWrite = async () => {
    if (!writePreview) return

    try {
      const result = await writeConfirm({
        formatted_content: writePreview.pending.formatted_content,
        folder: writePreview.pending.folder,
        file_name: writePreview.pending.file_name,
      })
      addMessage({
        id: `write-${Date.now()}`,
        role: 'assistant',
        content: result.message,
      })
      clearWritePreview()
    } catch (e) {
      addMessage({
        id: `err-${Date.now()}`,
        role: 'system',
        content: `❌ 写入失败：${(e as Error).message}`,
      })
    }
  }

  return (
    <div className="border-t border-mint-200 bg-white p-4">
      {/* 模式选择 */}
      <div className="mb-2">
        <ModeSelector />
      </div>

      {/* 写入确认按钮 */}
      {writePreview && (
        <div className="mb-2 flex gap-2">
          <button
            onClick={handleConfirmWrite}
            disabled={isStreaming}
            className="px-4 py-1.5 bg-mint-400 text-white text-sm rounded-lg hover:bg-mint-500 transition-colors disabled:opacity-50"
          >
            ✅ 确认写入天书
          </button>
          <button
            onClick={clearWritePreview}
            className="px-4 py-1.5 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200 transition-colors"
          >
            取消
          </button>
        </div>
      )}

      {/* 输入区域 */}
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder={
            isApiConfigured
              ? '输入消息...（Enter 发送，Shift+Enter 换行）'
              : '请先在设置中配置 API 地址'
          }
          className="flex-1 resize-none border border-mint-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-mint-400 focus:ring-2 focus:ring-mint-100 transition-all"
          rows={1}
          disabled={!isApiConfigured}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming || !isApiConfigured}
          className="px-5 py-2.5 bg-mint-400 text-white text-sm rounded-xl hover:bg-mint-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isStreaming ? '生成中...' : '发送'}
        </button>
      </div>
    </div>
  )
}
