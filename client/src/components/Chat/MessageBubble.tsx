/**
 * 消息气泡组件
 * 展示用户消息和 AI 回复，支持 Markdown 渲染和来源标注
 */
import { Markdown } from '../../utils/markdown'
import type { ChatMessage } from '../../store/chatStore'

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-mint-300 text-white rounded-br-md'
            : 'bg-white border border-mint-200 text-gray-800 rounded-bl-md shadow-sm'
        }`}
      >
        {/* 状态提示（流式输出中） */}
        {message.status && !isUser && (
          <div className="text-xs text-mint-500 mb-2 flex items-center gap-1">
            <span className="inline-block w-2 h-2 bg-mint-400 rounded-full animate-pulse" />
            {message.status}
          </div>
        )}

        {/* 消息内容 */}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <Markdown content={message.content} />
        )}

        {/* 流式光标 */}
        {message.isStreaming && !isUser && (
          <span className="inline-block w-2 h-4 bg-mint-400 ml-1 animate-pulse align-middle" />
        )}

        {/* 冲突提示 */}
        {message.hasConflict && !isUser && (
          <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
            ⚠ 信息冲突：{message.conflictSummary}
          </div>
        )}

        {/* 来源标注 */}
        {message.sources && message.sources.length > 0 && !isUser && (
          <div className="mt-2 pt-2 border-t border-mint-100">
            <div className="text-xs text-gray-400 mb-1">来源：</div>
            <div className="flex flex-wrap gap-1">
              {message.sources.map((src, i) => (
                <span
                  key={i}
                  className="text-xs bg-mint-50 text-mint-600 px-2 py-0.5 rounded"
                >
                  {src.folder}/{src.file_name}
                  {src.section && ` · ${src.section}`}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
