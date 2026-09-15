/**
 * 聊天窗口
 * 展示消息列表，自动滚动到底部
 */
import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import { MessageBubble } from './MessageBubble'

export function ChatWindow() {
  const { messages } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  // 新消息时自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-mint-50">
      {messages.length === 0 ? (
        // 空状态
        <div className="h-full flex flex-col items-center justify-center text-gray-400">
          <div className="w-16 h-16 rounded-2xl bg-mint-200 flex items-center justify-center text-3xl mb-4">
            🤖
          </div>
          <p className="text-lg font-medium text-gray-500">你好，我是秘书</p>
          <p className="text-sm mt-1">有什么可以帮你的？</p>
          <div className="mt-6 flex flex-col gap-2 text-xs">
            <p className="text-gray-400">💡 试试：</p>
            <p>· "项目A的进展是什么？"</p>
            <p>· "帮我做一个下周的工作计划"</p>
            <p>· "记下来：明天下午3点开会"</p>
          </div>
        </div>
      ) : (
        // 消息列表
        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
