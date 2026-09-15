/**
 * Preload 预加载脚本
 * 通过 contextBridge 向渲染进程暴露有限的安全 API
 * 渲染进程通过 window.mishu 调用，不直接访问 Node
 */
import { contextBridge, ipcRenderer } from 'electron'

// 暴露给渲染进程的 API
contextBridge.exposeInMainWorld('mishu', {
  // 窗口控制
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),

  // 桌面通知
  notify: (title: string, body: string) =>
    ipcRenderer.send('notify', { title, body }),

  // 本地配置读写（API 地址、主题等）
  getConfig: () => ipcRenderer.invoke('config:get'),
  setConfig: (config: Record<string, unknown>) =>
    ipcRenderer.invoke('config:set', config),
})
