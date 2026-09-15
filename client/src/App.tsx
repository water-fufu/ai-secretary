/**
 * App 根组件
 * 整合侧边栏 + 聊天页 + 知识库页 + 设置页
 */
import { useState, useEffect } from 'react'
import TitleBar from './components/Layout/TitleBar'
import { Sidebar, type PageType } from './components/Layout/Sidebar'
import { ChatWindow } from './components/Chat/ChatWindow'
import { InputBox } from './components/Chat/InputBox'
import { VaultOverview } from './components/Vault/VaultOverview'
import { SettingsPanel } from './components/Settings/SettingsPanel'
import { useConfigStore } from './store/configStore'

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('chat')
  const { loadConfig } = useConfigStore()

  // 启动时加载本地配置
  useEffect(() => {
    loadConfig()
  }, [])

  return (
    <div className="h-screen flex flex-col bg-mint-50 overflow-hidden">
      {/* 自定义标题栏 */}
      <TitleBar />

      {/* 主内容区：侧边栏 + 页面 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 侧边栏 */}
        <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />

        {/* 页面内容 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {currentPage === 'chat' && (
            <>
              <ChatWindow />
              <InputBox />
            </>
          )}
          {currentPage === 'vault' && <VaultOverview />}
          {currentPage === 'settings' && <SettingsPanel />}
        </div>
      </div>
    </div>
  )
}

export default App
