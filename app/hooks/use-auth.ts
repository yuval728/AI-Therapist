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
  const [isHydrated, setIsHydrated] = useState(false)
  const mountedRef = useRef(true)

  const checkAuth = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      const hasStoredToken = apiClient.isAuthenticated()
      
      if (hasStoredToken) {
        // Try to get user from localStorage first as a fallback
        let storedUserData = null
        if (typeof window !== "undefined") {
          const storedUser = localStorage.getItem("user")
          if (storedUser && mountedRef.current) {
            try {
              storedUserData = JSON.parse(storedUser)
              setUser(storedUserData)
            } catch (e) {
              // Failed to parse stored user data
            }
          }
        }
        
        // Then try to refresh from API (but don't block on it if it's slow)
        try {
          const userData = await apiClient.getCurrentUser()
          if (mountedRef.current) {
            setUser(userData)
          }
        } catch (apiError) {
          // If this is a timeout error and we have a stored user, that's okay
          if (apiError instanceof Error && apiError.message.includes("timeout") && storedUserData) {
            // Using localStorage user due to API timeout
          } else {
            // For other errors, we should probably clear the authentication
            if (mountedRef.current) {
              setUser(null)
              setError("Authentication check failed")
            }
          }
        }
      }
    } catch (err) {
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
    
    // Mark as hydrated when component mounts on client
    setIsHydrated(true)
    
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
      
      const authTokens = await apiClient.login(email, password)
      
      if (mountedRef.current) {
        setUser(authTokens.user)
        // Force an auth check to ensure state is consistent
        await checkAuth()
      }
      return authTokens
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
  }, [checkAuth])

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
    isAuthenticated: (() => {
      // Don't check auth status until after hydration to prevent SSR mismatch
      if (!isHydrated) {
        return false
      }
      
      // Check both user state AND token in localStorage to prevent race conditions
      const hasToken = apiClient.isAuthenticated()
      const hasUser = !!user
      
      // If we're still loading but have a token, we should consider the user authenticated
      // This prevents the race condition where the token exists but user data is still loading
      const authenticated = hasToken && (hasUser || loading)
      return authenticated
    })(),
    refresh: checkAuth,
  }
}
