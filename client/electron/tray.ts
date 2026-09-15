/**
 * 系统托盘管理
 * - 托盘图标 + 右键菜单
 * - 单击托盘图标：显示/隐藏窗口
 * - 关闭窗口时最小化到托盘（不退出应用）
 */
import { Tray, Menu, BrowserWindow, app, nativeImage } from 'electron'
import path from 'path'

// 全局托盘引用，防止被 GC
let tray: Tray | null = null

/**
 * 创建系统托盘
 * @param mainWindow 主窗口引用
 * @param onQuit 退出回调（设置 isQuitting 标记后真正退出）
 */
export function createTray(mainWindow: BrowserWindow, onQuit: () => void): void {
  // 托盘图标路径（开发环境用 resources，打包后用 process.resourcesPath）
  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, 'resources', 'icon.ico')
    : path.join(__dirname, '../resources/icon.ico')

  // 创建托盘图标（调整大小避免模糊）
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  tray = new Tray(icon)
  tray.setToolTip('秘书 - 个人知识库 AI Agent')

  // 右键菜单
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示秘书',
      click: () => {
        mainWindow.show()
        mainWindow.focus()
      },
    },
    {
      label: '隐藏窗口',
      click: () => {
        mainWindow.hide()
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        // 调用回调设置退出标记，然后真正退出
        onQuit()
        app.quit()
      },
    },
  ])

  tray.setContextMenu(contextMenu)

  // 单击托盘图标：切换显示/隐藏
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

/**
 * 更新托盘提示文字
 */
export function setTrayTooltip(tooltip: string): void {
  if (tray) {
    tray.setToolTip(tooltip)
  }
}

/**
 * 销毁托盘（应用退出时调用）
 */
export function destroyTray(): void {
  if (tray) {
    tray.destroy()
    tray = null
  }
}
