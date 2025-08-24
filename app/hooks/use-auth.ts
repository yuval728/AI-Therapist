"use client"

import { useState, useEffect } from "react"
import { apiClient } from "@/lib/api"

interface User {
  id: string
  email: string
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkAuth()

    const handleAuthLogout = () => {
      setUser(null)
      setError(null)
    }

    const handleStorage = (e: StorageEvent) => {
      if (e.key === "access_token" && !e.newValue) {
        setUser(null)
        setError(null)
      }
    }

    const setupEventListeners = () => {
      if (typeof window !== "undefined") {
        window.addEventListener("auth:logout", handleAuthLogout)
        window.addEventListener("storage", handleStorage)
      }
    }

    const cleanupEventListeners = () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("auth:logout", handleAuthLogout)
        window.removeEventListener("storage", handleStorage)
      }
    }

    setupEventListeners()
    return cleanupEventListeners
  }, [])

  const checkAuth = async () => {
    try {
      if (apiClient.isAuthenticated()) {
        const userData = await apiClient.getCurrentUser()
        setUser(userData)
      }
    } catch (err) {
      console.error("Auth check failed:", err)
      setError(err instanceof Error ? err.message : "Authentication failed")
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      setError(null)
      setLoading(true)
      const response = await apiClient.login(email, password)
      const userData = await apiClient.getCurrentUser()
      setUser(userData)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Login failed"
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const signup = async (email: string, password: string, fullName?: string) => {
    try {
      setError(null)
      setLoading(true)
      const result = await apiClient.signup(email, password, fullName)
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Signup failed"
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    apiClient.logout()
    setUser(null)
    setError(null)
  }

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
