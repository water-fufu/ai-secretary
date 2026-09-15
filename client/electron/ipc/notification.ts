/**
 * 桌面通知 IPC 处理器
 * 渲染进程通过 window.mishu.notify(title, body) 发送通知请求
 */
import { ipcMain, Notification } from 'electron'
import path from 'path'

/**
 * 注册通知相关的 IPC 通道
 */
export function registerNotificationIpc(): void {
  ipcMain.on('notify', (_event, payload: { title: string; body: string }) => {
    const { title, body } = payload

    // 检查系统是否支持通知
    if (!Notification.isSupported()) {
      console.warn('[通知] 当前系统不支持桌面通知')
      return
    }

    // 构建通知（图标使用 resources 目录下的图标）
    const notification = new Notification({
      title,
      body,
      silent: false,
    })

    notification.show()
  })
}
