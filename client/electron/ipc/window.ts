/**
 * 窗口控制 IPC 处理器
 * 渲染进程通过 window.mishu.minimize() / close() 发送消息，这里处理
 */
import { ipcMain, BrowserWindow } from 'electron'

/**
 * 注册窗口控制相关的 IPC 通道
 */
export function registerWindowIpc(): void {
  // 最小化窗口
  ipcMain.on('window:minimize', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      win.minimize()
    }
  })

  // 最大化/还原窗口
  ipcMain.on('window:maximize', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      if (win.isMaximized()) {
        win.unmaximize()
      } else {
        win.maximize()
      }
    }
  })

  // 关闭窗口（P1 直接关闭，P2 改为最小化到托盘）
  ipcMain.on('window:close', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      win.close()
    }
  })
}
