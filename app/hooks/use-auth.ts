"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { apiClient } from "@/lib/api"

interface User {
  id: string
  email: string
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  const checkAuth = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      if (apiClient.isAuthenticated()) {
        const userData = await apiClient.getCurrentUser()
        if (mountedRef.current) {
          setUser(userData)
        }
      }
    } catch (err) {
      console.error("Auth check failed:", err)
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : "Authentication failed")
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    checkAuth()

    const handleAuthLogout = () => {
      if (mountedRef.current) {
        setUser(null)
        setError(null)
      }
    }

    const handleStorage = (e: StorageEvent) => {
      if (e.key === "access_token" && !e.newValue && mountedRef.current) {
        setUser(null)
        setError(null)
      }
    }

    if (typeof window !== "undefined") {
      window.addEventListener("auth:logout", handleAuthLogout)
      window.addEventListener("storage", handleStorage)
    }

    return () => {
      mountedRef.current = false
      if (typeof window !== "undefined") {
        window.removeEventListener("auth:logout", handleAuthLogout)
        window.removeEventListener("storage", handleStorage)
      }
    }
  }, [checkAuth])

  const login = useCallback(async (email: string, password: string) => {
    try {
      setError(null)
      setLoading(true)
      const response = await apiClient.login(email, password)
      const userData = await apiClient.getCurrentUser()
      if (mountedRef.current) {
        setUser(userData)
      }
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Login failed"
      if (mountedRef.current) {
        setError(errorMessage)
      }
      throw new Error(errorMessage)
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const signup = useCallback(async (email: string, password: string, fullName?: string) => {
    try {
      setError(null)
      setLoading(true)
      const result = await apiClient.signup(email, password, fullName)
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Signup failed"
      if (mountedRef.current) {
        setError(errorMessage)
      }
      throw new Error(errorMessage)
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const logout = useCallback(() => {
    apiClient.logout()
    if (mountedRef.current) {
      setUser(null)
      setError(null)
    }
  }, [])

  return {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    isAuthenticated: !!user,
    refresh: checkAuth,
  }
}
