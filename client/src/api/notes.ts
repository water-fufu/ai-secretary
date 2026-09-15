/**
 * 笔记相关 API
 */
import apiClient from './client'
import type { Note, NoteListResponse } from '../types/api'

/**
 * 获取笔记列表
 */
export async function listNotes(
  folder?: string,
  page = 1,
  pageSize = 20,
): Promise<NoteListResponse> {
  const params: any = { page, page_size: pageSize }
  if (folder) params.folder = folder
  const { data } = await apiClient.get('/api/v1/notes', { params })
  return data
}

/**
 * 获取笔记详情
 */
export async function getNote(noteId: number): Promise<Note> {
  const { data } = await apiClient.get(`/api/v1/notes/${noteId}`)
  return data
}

/**
 * 创建笔记
 */
export async function createNote(note: {
  folder: string
  file_name: string
  content: string
  title?: string
}): Promise<Note> {
  const { data } = await apiClient.post('/api/v1/notes', note)
  return data
}

/**
 * 删除笔记
 */
export async function deleteNote(noteId: number): Promise<void> {
  await apiClient.delete(`/api/v1/notes/${noteId}`)
}
