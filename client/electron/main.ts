/**
 * Electron 主进程入口
 * 职责：创建窗口、管理生命周期、托盘、全局快捷键、通知、配置
 */
import { app, BrowserWindow, shell, globalShortcut } from 'electron'
import path from 'path'
import { registerWindowIpc } from './ipc/window'
import { registerNotificationIpc } from './ipc/notification'
import { registerConfigIpc } from './ipc/config'
import { createTray, destroyTray } from './tray'

// 全局引用主窗口，防止被 GC 回收
let mainWindow: BrowserWindow | null = null

// 标记是否真正退出（托盘菜单"退出"时设为 true）
let isQuitting = false

// 全局快捷键（可通过配置修改）
const GLOBAL_SHORTCUT = 'CommandOrControl+Alt+M'

/**
 * 创建主窗口
 * - 无边框（自定义标题栏在渲染进程实现）
 * - contextIsolation 开启，nodeIntegration 关闭（安全最佳实践）
 */
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false, // 隐藏默认标题栏，用自定义 TitleBar
    titleBarStyle: 'hidden',
    backgroundColor: '#F5FFFA',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, // 安全：隔离渲染进程
      nodeIntegration: false, // 安全：禁用 Node 集成
      sandbox: false, // preload 需要访问 Node API
    },
  })

  // 开发环境加载 Vite dev server，生产环境加载构建后的 index.html
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    // 开发环境自动打开 DevTools
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 外部链接在系统浏览器打开，不在应用内打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  // 关闭按钮：最小化到托盘而非退出（P2 核心特性）
  mainWindow.on('close', (e) => {
    // 只有 isQuitting 为 true 时才真正退出
    if (!isQuitting) {
      e.preventDefault()
      mainWindow?.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

/**
 * 注册全局快捷键
 * Ctrl+Alt+M：唤起/隐藏秘书窗口
 */
function registerGlobalShortcut(): void {
  const success = globalShortcut.register(GLOBAL_SHORTCUT, () => {
    if (!mainWindow) {
      createWindow()
      return
    }
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })

  if (success) {
    console.log(`[快捷键] 已注册全局快捷键: ${GLOBAL_SHORTCUT}`)
  } else {
    console.warn(`[快捷键] 注册失败: ${GLOBAL_SHORTCUT}（可能被其他程序占用）`)
  }
}

// Electron 就绪后创建窗口
app.whenReady().then(() => {
  // 注册所有 IPC 处理器
  registerWindowIpc()
  registerNotificationIpc()
  registerConfigIpc()

  // 创建窗口
  createWindow()

  // 创建系统托盘
  if (mainWindow) {
    createTray(mainWindow, () => {
      isQuitting = true
    })
  }

  // 注册全局快捷键
  registerGlobalShortcut()

  // macOS 上点击 Dock 图标时重新创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 应用退出前：注销全局快捷键、销毁托盘
app.on('will-quit', () => {
  globalShortcut.unregisterAll()
  destroyTray()
})

// 所有窗口关闭时不退出（托盘仍在运行），macOS 除外的默认行为已被 close 事件拦截
app.on('window-all-closed', () => {
  // 不调用 app.quit()，让应用在托盘继续运行
  // 用户通过托盘菜单"退出"才真正退出
})
