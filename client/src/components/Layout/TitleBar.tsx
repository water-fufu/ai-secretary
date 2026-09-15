/**
 * 自定义标题栏组件
 * - 左侧：应用图标 + 标题
 * - 中间：可拖拽区域（-webkit-app-region: drag）
 * - 右侧：最小化 / 关闭按钮
 * 因为主进程设置了 frame: false，所以需要自己实现标题栏
 */
import { useState } from 'react'

function TitleBar() {
  // 鼠标悬停状态，用于按钮高亮
  const [hoverBtn, setHoverBtn] = useState<string | null>(null)

  return (
    <div
      className="h-10 flex items-center justify-between bg-white border-b border-mint-200 select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      {/* 左侧：图标 + 标题 */}
      <div className="flex items-center gap-2 px-3">
        <div className="w-5 h-5 rounded bg-mint-300 flex items-center justify-center text-xs font-bold text-white">
          秘
        </div>
        <span className="text-sm font-medium text-gray-700">秘书</span>
      </div>

      {/* 右侧：窗口控制按钮 */}
      <div
        className="flex items-center h-full"
        style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      >
        {/* 最小化按钮 */}
        <button
          className="w-11 h-full flex items-center justify-center text-gray-500 hover:bg-mint-100 transition-colors"
          onClick={() => window.mishu?.minimize()}
          onMouseEnter={() => setHoverBtn('minimize')}
          onMouseLeave={() => setHoverBtn(null)}
          title="最小化"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <rect y="5" width="12" height="2" rx="1" />
          </svg>
        </button>

        {/* 关闭按钮 */}
        <button
          className={`w-11 h-full flex items-center justify-center transition-colors ${
            hoverBtn === 'close'
              ? 'bg-red-500 text-white'
              : 'text-gray-500 hover:bg-red-100'
          }`}
          onClick={() => window.mishu?.close()}
          onMouseEnter={() => setHoverBtn('close')}
          onMouseLeave={() => setHoverBtn(null)}
          title="关闭"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <line x1="2" y1="2" x2="10" y2="10" />
            <line x1="10" y1="2" x2="2" y2="10" />
          </svg>
        </button>
      </div>
    </div>
  )
}

export default TitleBar
