/**
 * API 客户端封装
 * baseURL 从本地配置读取（用户在设置页配置）
 */
import axios from 'axios'
import type { AppConfig } from '../types/electron'

// 获取 API base URL
async function getBaseURL(): Promise<string> {
  try {
    const config: AppConfig = await window.mishu.getConfig()
    return config.apiBaseUrl || ''
  } catch {
    return ''
  }
}

// 创建 axios 实例
const apiClient = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：动态设置 baseURL
apiClient.interceptors.request.use(async (config) => {
  const baseURL = await getBaseURL()
  config.baseURL = baseURL
  return config
})

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.message)
    return Promise.reject(error)
  },
)

export default apiClient
