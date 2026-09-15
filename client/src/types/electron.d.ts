/**
 * window.mishu API 的 TypeScript 类型声明
 * 由 preload.ts 通过 contextBridge 暴露
 */
export interface MishuAPI {
  // 窗口控制
  minimize: () => void
  maximize: () => void
  close: () => void

  // 桌面通知
  notify: (title: string, body: string) => void

  // 本地配置
  getConfig: () => Promise<AppConfig>
  setConfig: (config: Partial<AppConfig>) => Promise<void>
}

/**
 * 应用配置（存储在本地，electron-store）
 */
export interface AppConfig {
  // 云端 API 地址（CloudBase 部署后填入），默认留空
  apiBaseUrl: string
  // 主题：light / dark
  theme: 'light' | 'dark'
  // 是否启用桌面通知
  notificationEnabled: boolean
  // 全局快捷键
  shortcut: string
}

declare global {
  interface Window {
    mishu: MishuAPI
  }
}

export {}
