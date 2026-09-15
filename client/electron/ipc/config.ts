/**
 * 本地配置 IPC 处理器
 * 使用 electron-store 将配置持久化到本地
 * P1 先用简单的 JSON 文件存储，P2 可引入 electron-store
 */
import { ipcMain, app } from 'electron'
import path from 'path'
import fs from 'fs'
import type { AppConfig } from '../../src/types/electron'

// 配置文件路径（存放在用户数据目录）
const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json')

// 默认配置
const DEFAULT_CONFIG: AppConfig = {
  apiBaseUrl: '', // 默认留空，用户在设置页配置
  theme: 'light',
  notificationEnabled: true,
  shortcut: 'CommandOrControl+Alt+M',
}

/**
 * 读取配置文件，不存在则返回默认配置
 */
function readConfig(): AppConfig {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const raw = fs.readFileSync(CONFIG_PATH, 'utf-8')
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
    }
  } catch (e) {
    console.error('[配置] 读取失败，使用默认配置:', e)
  }
  return { ...DEFAULT_CONFIG }
}

/**
 * 写入配置文件
 */
function writeConfig(config: AppConfig): void {
  try {
    const dir = path.dirname(CONFIG_PATH)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8')
  } catch (e) {
    console.error('[配置] 写入失败:', e)
  }
}

/**
 * 注册配置相关的 IPC 通道
 */
export function registerConfigIpc(): void {
  // 读取配置
  ipcMain.handle('config:get', () => {
    return readConfig()
  })

  // 写入配置（合并更新）
  ipcMain.handle('config:set', (_event, partial: Partial<AppConfig>) => {
    const current = readConfig()
    const updated = { ...current, ...partial }
    writeConfig(updated)
    return updated
  })
}
