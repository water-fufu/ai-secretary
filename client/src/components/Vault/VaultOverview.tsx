/**
 * 知识库管理页
 * 展示知识库概览、笔记列表
 */
import { useState, useEffect } from 'react'
import { getVaultOverview, refreshVault } from '../../api/vault'
import { listNotes } from '../../api/notes'
import type { VaultStats, Note } from '../../types/api'
import { useConfigStore } from '../../store/configStore'

export function VaultOverview() {
  const [stats, setStats] = useState<VaultStats | null>(null)
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const { config } = useConfigStore()

  const isApiConfigured = config?.apiBaseUrl && config.apiBaseUrl.length > 0

  // 加载数据
  const loadData = async () => {
    if (!isApiConfigured) return
    setLoading(true)
    try {
      const [vaultStats, noteList] = await Promise.all([
        getVaultOverview(),
        listNotes(),
      ])
      setStats(vaultStats)
      setNotes(noteList.items)
    } catch (e) {
      console.error('加载知识库数据失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [config?.apiBaseUrl])

  /**
   * 重建索引
   */
  const handleRefresh = async () => {
    if (!isApiConfigured) return
    setRefreshing(true)
    try {
      await refreshVault()
      await loadData()
    } catch (e) {
      console.error('重建索引失败:', e)
    } finally {
      setRefreshing(false)
    }
  }

  if (!isApiConfigured) {
    return (
      <div className="flex-1 flex items-center justify-center bg-mint-50">
        <div className="text-center text-gray-400">
          <div className="text-4xl mb-3">📚</div>
          <p>请先在设置中配置 API 地址</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-mint-50">
      <div className="max-w-4xl mx-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-800">📚 知识库</h2>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-mint-400 text-white text-sm rounded-lg hover:bg-mint-500 transition-colors disabled:opacity-50"
          >
            {refreshing ? '重建中...' : '🔄 重建索引'}
          </button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard label="分区数量" value={stats?.folder_count || 0} icon="📁" />
          <StatCard label="笔记总数" value={stats?.file_count || 0} icon="📝" />
          <StatCard label="切片总数" value={stats?.chunk_count || 0} icon="🧩" />
          <StatCard label="已索引" value={stats?.vector_indexed || 0} icon="🔍" />
        </div>

        {/* 文件夹列表 */}
        {stats?.folders && stats.folders.length > 0 && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-mint-200 mb-6">
            <h3 className="font-medium text-gray-700 mb-3">分区</h3>
            <div className="flex flex-wrap gap-2">
              {stats.folders.map((folder) => (
                <span
                  key={folder}
                  className="px-3 py-1 bg-mint-50 text-mint-600 text-sm rounded-full"
                >
                  📁 {folder}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 笔记列表 */}
        <div className="bg-white rounded-xl shadow-sm border border-mint-200">
          <div className="p-4 border-b border-mint-100">
            <h3 className="font-medium text-gray-700">笔记列表</h3>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-400">加载中...</div>
          ) : notes.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <div className="text-3xl mb-2">📭</div>
              <p>暂无笔记，去聊天页写入一些内容吧</p>
            </div>
          ) : (
            <div className="divide-y divide-mint-50">
              {notes.map((note) => (
                <div key={note.id} className="p-4 hover:bg-mint-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-700 text-sm">
                        📝 {note.file_name}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        📁 {note.folder} · {new Date(note.updated_at).toLocaleString('zh-CN')}
                      </div>
                    </div>
                    <span className="text-xs text-gray-400">
                      {note.content.length} 字
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-mint-200 text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-mint-600">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
    </div>
  )
}
