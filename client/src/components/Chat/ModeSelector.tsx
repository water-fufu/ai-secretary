/**
 * 模式选择器
 * auto / qa / plan / write / claude
 */
import { useChatStore } from '../../store/chatStore'
import type { ChatMode } from '../../types/api'

const MODES: { value: ChatMode; label: string; icon: string }[] = [
  { value: 'auto', label: '自动识别', icon: '🤖' },
  { value: 'qa', label: '知识库问答', icon: '💬' },
  { value: 'plan', label: '生成计划', icon: '📋' },
  { value: 'write', label: '写入天书', icon: '✍️' },
  { value: 'claude', label: 'Claude指令', icon: '🎯' },
]

export function ModeSelector() {
  const { currentMode, setMode } = useChatStore()

  return (
    <div className="flex items-center gap-1">
      {MODES.map((mode) => (
        <button
          key={mode.value}
          onClick={() => setMode(mode.value)}
          className={`px-2 py-1 text-xs rounded-md transition-colors ${
            currentMode === mode.value
              ? 'bg-mint-300 text-white'
              : 'text-gray-500 hover:bg-mint-50'
          }`}
          title={mode.label}
        >
          <span className="mr-1">{mode.icon}</span>
          {mode.label}
        </button>
      ))}
    </div>
  )
}
