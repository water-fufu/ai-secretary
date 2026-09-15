/**
 * 设置页
 * API 地址配置、主题、通知等
 */
import { useState, useEffect } from 'react'
import { useConfigStore } from '../../store/configStore'
import { healthCheck } from '../../api/vault'

export function SettingsPanel() {
  const { config, loadConfig, updateConfig } = useConfigStore()
  const [apiUrl, setApiUrl] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  useEffect(() => {
    if (config) {
      setApiUrl(config.apiBaseUrl)
    }
  }, [config])

  /**
   * 保存 API 地址
   */
  const handleSave = async () => {
    await updateConfig({ apiBaseUrl: apiUrl.trim() })
    setTestResult('✅ 配置已保存')
    setTimeout(() => setTestResult(null), 3000)
  }

  /**
   * 测试连接
   */
  const handleTest = async () => {
    if (!apiUrl.trim()) {
      setTestResult('⚠ 请先输入 API 地址')
      return
    }

    setTesting(true)
    setTestResult(null)

    // 临时保存配置以便测试
    await updateConfig({ apiBaseUrl: apiUrl.trim() })

    try {
      const result = await healthCheck()
      setTestResult(`✅ 连接成功！服务版本：v${result.version}`)
    } catch (e) {
      setTestResult(`❌ 连接失败：${(e as Error).message}`)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-mint-50">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-xl font-bold text-gray-800 mb-6">⚙️ 设置</h2>

        {/* API 配置 */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-mint-200 mb-6">
          <h3 className="font-medium text-gray-700 mb-4">云端 API 配置</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                API 地址（CloudBase 云托管域名）
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://your-service.tcloudbaseapp.com"
                className="w-full px-3 py-2 border border-mint-200 rounded-lg text-sm focus:outline-none focus:border-mint-400 focus:ring-2 focus:ring-mint-100"
              />
              <p className="text-xs text-gray-400 mt-1">
                部署到 CloudBase 云托管后，将服务域名填入此处
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-mint-400 text-white text-sm rounded-lg hover:bg-mint-500 transition-colors"
              >
                保存配置
              </button>
              <button
                onClick={handleTest}
                disabled={testing}
                className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                {testing ? '测试中...' : '测试连接'}
              </button>
            </div>

            {testResult && (
              <div className="text-sm text-gray-600 p-2 bg-mint-50 rounded-lg">
                {testResult}
              </div>
            )}
          </div>
        </div>

        {/* 关于 */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-mint-200">
          <h3 className="font-medium text-gray-700 mb-4">关于</h3>
          <div className="text-sm text-gray-500 space-y-1">
            <p>秘书 2.0 - 个人知识库 AI Agent</p>
            <p>技术栈：Electron + React + FastAPI + MySQL + Redis</p>
            <p>版本：2.0.0</p>
          </div>
        </div>
      </div>
    </div>
  )
}
