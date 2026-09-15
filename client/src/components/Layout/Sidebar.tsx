/**
 * 侧边栏导航
 * 聊天 / 知识库 / 设置
 */
import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'

export type PageType = 'chat' | 'vault' | 'settings'

interface SidebarProps {
  currentPage: PageType
  onPageChange: (page: PageType) => void
}

const NAV_ITEMS: { key: PageType; label: string; icon: string }[] = [
  { key: 'chat', label: '秘书对话', icon: '💬' },
  { key: 'vault', label: '知识库', icon: '📚' },
  { key: 'settings', label: '设置', icon: '⚙️' },
]

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const { clearMessages } = useChatStore()

  const handleNavClick = (page: PageType) => {
    onPageChange(page)
    if (page === 'chat') {
      // 切换到聊天页不清除消息
    }
  }

  return (
    <div className="w-48 bg-white border-r border-mint-200 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-mint-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-mint-300 flex items-center justify-center text-white font-bold text-sm">
            秘
          </div>
          <span className="font-bold text-gray-700">秘书 2.0</span>
        </div>
      </div>

      {/* 导航 */}
      <nav className="flex-1 p-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            onClick={() => handleNavClick(item.key)}
            className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-colors mb-1 ${
              currentPage === item.key
                ? 'bg-mint-100 text-mint-600 font-medium'
                : 'text-gray-600 hover:bg-mint-50'
            }`}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {/* 底部操作 */}
      <div className="p-2 border-t border-mint-100">
        <button
          onClick={clearMessages}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-mint-50 transition-colors"
        >
          <span>🗑️</span>
          清空对话
        </button>
      </div>
    </div>
  )
}
