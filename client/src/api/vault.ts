/**
 * 知识库相关 API
 */
import apiClient from './client'
import type { VaultStats } from '../types/api'

/**
 * 获取知识库概览
 */
export async function getVaultOverview(): Promise<VaultStats> {
  const { data } = await apiClient.get('/api/v1/vault/overview')
  return data
}

/**
 * 重建知识库索引
 */
export async function refreshVault(): Promise<{
  message: string
  chunk_count: number
  note_count: number
}> {
  const { data } = await apiClient.post('/api/v1/vault/refresh')
  return data
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{
  status: string
  version: string
}> {
  const { data } = await apiClient.get('/api/v1/health')
  return data
}
