"use client"

import { useState, useCallback } from "react"
import { apiClient, type TherapySession } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

interface SessionState {
  sessions: TherapySession[]
  activeSessionId: string | null
  loading: boolean
  error: string | null
  hasMore: boolean
}

export function useSessionManagement() {
  const [state, setState] = useState<SessionState>({
    sessions: [],
    activeSessionId: null,
    loading: false,
    error: null,
    hasMore: true,
  })

  const { toast } = useToast()

  // Load sessions from API
  const loadSessions = useCallback(
    async (offset = 0, limit = 50, append = false) => {
      try {
        setState((prev) => ({ ...prev, loading: true, error: null }))

        const sessions = await apiClient.getSessions(offset, limit)

        setState((prev) => ({
          ...prev,
          sessions: (() => {
            const incoming = append ? [...prev.sessions, ...sessions] : sessions
            const seen = new Set<string>()
            const deduped: TherapySession[] = []
            for (const s of incoming) {
              if (!seen.has(s.id)) {
                seen.add(s.id)
                deduped.push(s)
              }
            }
            return deduped
          })(),
          hasMore: sessions.length === limit,
          loading: false,
        }))

        return sessions
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Failed to load sessions"
        setState((prev) => ({
          ...prev,
          error: errorMessage,
          loading: false,
        }))

        if (errorMessage === "Session expired") {
          // Handle auth error - will be caught by auth system
          throw error
        }

        toast({
          title: "Error loading sessions",
          description: errorMessage,
          variant: "destructive",
        })

        return []
      }
    },
    [toast],
  )

  // Create new session
  const createSession = useCallback(
    async (emotion?: string, crisis_level?: number, metadata?: Record<string, any>) => {
      try {
        setState((prev) => ({ ...prev, loading: true, error: null }))

        const newSession = await apiClient.createSession(emotion, crisis_level, metadata)

        setState((prev) => ({
          ...prev,
          sessions: [
            newSession,
            ...prev.sessions.filter((s) => s.id !== newSession.id),
          ],
          activeSessionId: newSession.id,
          loading: false,
        }))

        // Persist active session
        if (typeof window !== "undefined") {
          localStorage.setItem("activeSessionId", newSession.id)
        }

        toast({
          title: "New session created",
          description: "Started a new therapy session",
        })

        return newSession
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Failed to create session"
        setState((prev) => ({
          ...prev,
          error: errorMessage,
          loading: false,
        }))

        toast({
          title: "Error creating session",
          description: errorMessage,
          variant: "destructive",
        })

        throw error
      }
    },
    [toast],
  )

  // Set active session
  const setActiveSession = useCallback((sessionId: string | null) => {
    setState((prev) => ({ ...prev, activeSessionId: sessionId }))

    // Persist active session
    if (typeof window !== "undefined") {
      if (sessionId) {
        localStorage.setItem("activeSessionId", sessionId)
      } else {
        localStorage.removeItem("activeSessionId")
      }
    }
  }, [])

  // Get active session
  const getActiveSession = useCallback(() => {
    return state.sessions.find((session) => session.id === state.activeSessionId) || null
  }, [state.sessions, state.activeSessionId])

  // Load more sessions (for infinite scroll)
  const loadMoreSessions = useCallback(() => {
    if (!state.loading && state.hasMore) {
      loadSessions(state.sessions.length, 50, true)
    }
  }, [state.loading, state.hasMore, state.sessions.length, loadSessions])

  // Initialize sessions and restore active session
  const initializeSessions = useCallback(async () => {
    try {
      // Load sessions
      const sessions = await loadSessions()

      // Restore active session from localStorage
      if (typeof window !== "undefined") {
        const savedActiveSessionId = localStorage.getItem("activeSessionId")
        if (savedActiveSessionId && sessions.some((s) => s.id === savedActiveSessionId)) {
          setState((prev) => ({ ...prev, activeSessionId: savedActiveSessionId }))
        } else if (sessions.length > 0) {
          // If no saved session or saved session not found, use the most recent one
          const mostRecent = sessions[0]
          setState((prev) => ({ ...prev, activeSessionId: mostRecent.id }))
          localStorage.setItem("activeSessionId", mostRecent.id)
        }
      }
    } catch (error) {
      console.error("Failed to initialize sessions:", error)
    }
  }, [loadSessions])

  // Search sessions
  const searchSessions = useCallback(
    (query: string) => {
      if (!query.trim()) {
        return state.sessions
      }

      const lowercaseQuery = query.toLowerCase()
      return state.sessions.filter(
        (session) =>
          session.emotion?.toLowerCase().includes(lowercaseQuery) ||
          session.metadata?.title?.toLowerCase().includes(lowercaseQuery) ||
          new Date(session.created_at).toLocaleDateString().includes(lowercaseQuery),
      )
    },
    [state.sessions],
  )

  return {
    sessions: state.sessions,
    activeSessionId: state.activeSessionId,
    loading: state.loading,
    error: state.error,
    hasMore: state.hasMore,
    loadSessions,
    createSession,
    setActiveSession,
    getActiveSession,
    loadMoreSessions,
    initializeSessions,
    searchSessions,
  }
}
