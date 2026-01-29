/**
 * 认证相关的 React Hook
 */
import { useCallback } from 'react'

/**
 * 认证 Hook
 * 提供认证状态检查和 token 管理
 */
export const useAuth = () => {
  /**
   * 检查用户是否已认证
   */
  const isAuthenticated = useCallback((): boolean => {
    const token = localStorage.getItem('access_token')
    return !!token
  }, [])

  /**
   * 获取当前 token
   */
  const getToken = useCallback((): string | null => {
    return localStorage.getItem('access_token')
  }, [])

  return {
    isAuthenticated,
    getToken,
  }
}
