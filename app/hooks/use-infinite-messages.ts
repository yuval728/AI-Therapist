"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { handleApiError } from "@/lib/error-handler"

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, unknown>
}

interface InfiniteMessagesState {
  messages: ChatMessage[]
  loading: boolean
  loadingMore: boolean
  error: string | null
  hasMore: boolean
  total: number
  initialized: boolean
}

const INITIAL_LOAD_SIZE = 20
const LOAD_MORE_SIZE = 15

export function useInfiniteMessages(sessionId?: string) {
  const [state, setState] = useState<InfiniteMessagesState>({
    messages: [],
    loading: false,
    loadingMore: false,
    error: null,
    hasMore: false,
    total: 0,
    initialized: false,
  })

  const mountedRef = useRef(true)
  const { toast } = useToast()

  // Reset state when session changes
  useEffect(() => {
    setState({
      messages: [],
      loading: false,
      loadingMore: false,
      error: null,
      hasMore: false,
      total: 0,
      initialized: false,
    })
  }, [sessionId])

  // Initial load of recent messages
  const loadInitialMessages = useCallback(async () => {
    if (!sessionId || state.loading || state.initialized) return

    try {
      setState(prev => ({ ...prev, loading: true, error: null }))

      const response = await apiClient.getSessionMessagesPaged(sessionId, 0, INITIAL_LOAD_SIZE)
      
      if (!mountedRef.current) return

      const messages = response.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.created_at,
        emotion: m.emotion,
        crisis_level: m.crisis_level,
        mode: m.mode,
        metadata: m.metadata,
      }))

      // Messages come in chronological order, we want most recent at bottom
      setState(prev => ({
        ...prev,
        messages: messages.reverse(), // Reverse to show oldest first
        total: response.total,
        hasMore: response.total > INITIAL_LOAD_SIZE,
        loading: false,
        initialized: true,
      }))

    } catch (error) {
      if (!mountedRef.current) return

      const errorMessage = error instanceof Error ? error.message : "Failed to load messages"
      setState(prev => ({
        ...prev,
        error: errorMessage,
        loading: false,
        initialized: true,
      }))

      handleApiError(error instanceof Error ? error : new Error(errorMessage), {
        component: "useInfiniteMessages",
        action: "loadInitialMessages",
        sessionId,
      })

      toast({
        title: "Failed to load messages",
        description: errorMessage,
        variant: "destructive",
      })
    }
  }, [sessionId, state.loading, state.initialized, toast])

  // Load older messages (for infinite scroll)
  const loadMoreMessages = useCallback(async () => {
    if (!sessionId || state.loadingMore || !state.hasMore || !state.initialized) return

    try {
      setState(prev => ({ ...prev, loadingMore: true, error: null }))

      // Load older messages from before the oldest message we have
      const currentOffset = state.messages.length
      const response = await apiClient.getSessionMessagesPaged(sessionId, currentOffset, LOAD_MORE_SIZE)
      
      if (!mountedRef.current) return

      const olderMessages = response.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.created_at,
        emotion: m.emotion,
        crisis_level: m.crisis_level,
        mode: m.mode,
        metadata: m.metadata,
      }))

      // Prepend older messages (they come in chronological order)
      setState(prev => ({
        ...prev,
        messages: [...olderMessages.reverse(), ...prev.messages],
        hasMore: prev.messages.length + olderMessages.length < response.total,
        loadingMore: false,
      }))

    } catch (error) {
      if (!mountedRef.current) return

      const errorMessage = error instanceof Error ? error.message : "Failed to load older messages"
      setState(prev => ({
        ...prev,
        error: errorMessage,
        loadingMore: false,
      }))

      handleApiError(error instanceof Error ? error : new Error(errorMessage), {
        component: "useInfiniteMessages",
        action: "loadMoreMessages",
        sessionId,
      })

      toast({
        title: "Failed to load older messages",
        description: errorMessage,
        variant: "destructive",
      })
    }
  }, [sessionId, state.loadingMore, state.hasMore, state.initialized, state.messages.length, toast])

  // Add a new message (for real-time updates)
  const addMessage = useCallback((message: ChatMessage) => {
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, message],
      total: prev.total + 1,
    }))
  }, [])

  // Initialize messages when session is available
  useEffect(() => {
    if (sessionId && !state.initialized) {
      loadInitialMessages()
    }
  }, [sessionId, state.initialized, loadInitialMessages])

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  return {
    messages: state.messages,
    loading: state.loading,
    loadingMore: state.loadingMore,
    error: state.error,
    hasMore: state.hasMore,
    total: state.total,
    initialized: state.initialized,
    loadMoreMessages,
    addMessage,
  }
}
