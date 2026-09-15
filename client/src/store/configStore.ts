/**
 * 配置状态管理
 * 管理 API 地址、主题等本地配置
 */
import { create } from 'zustand'
import type { AppConfig } from '../types/electron'

interface ConfigState {
  config: AppConfig | null
  isLoaded: boolean

  loadConfig: () => Promise<void>
  updateConfig: (updates: Partial<AppConfig>) => Promise<void>
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: null,
  isLoaded: false,

  loadConfig: async () => {
    try {
      const config = await window.mishu.getConfig()
      set({ config, isLoaded: true })
    } catch (e) {
      console.error('加载配置失败:', e)
      set({
        config: {
          apiBaseUrl: '',
          theme: 'light',
          notificationEnabled: true,
          shortcut: 'CommandOrControl+Alt+M',
        },
        isLoaded: true,
      })
    }
  },

  updateConfig: async (updates) => {
    const current = get().config
    if (!current) return

    const updated = { ...current, ...updates }
    try {
      await window.mishu.setConfig(updated)
      set({ config: updated })
    } catch (e) {
      console.error('保存配置失败:', e)
    }
  },
}))
