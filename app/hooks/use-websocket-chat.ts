"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { WebSocketClient, type WebSocketMessage, type ConnectionStatus } from "@/lib/websocket-client"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, any>
}

interface StreamingState {
  content: string
  isStreaming: boolean
  metadata?: {
    emotion?: string
    crisis_level?: number
    mode?: string
    metadata?: Record<string, any>
  }
}

const createChatMessage = (role: "user" | "assistant", content: string, extra?: Partial<ChatMessage>): ChatMessage => ({
  id: `msg-${Date.now()}`,
  role,
  content,
  timestamp: new Date().toISOString(),
  ...extra,
})

export function useWebSocketChat(sessionId?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected")
  const [isTyping, setIsTyping] = useState(false)
  const [streamingState, setStreamingState] = useState<StreamingState>({
    content: "",
    isStreaming: false,
  })
  const [error, setError] = useState<string | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [pageSize] = useState(20)
  const [totalMessages, setTotalMessages] = useState<number>(0)
  const [offset, setOffset] = useState<number>(0) // current window start offset (for ascending order)

  const wsClient = useRef<WebSocketClient | null>(null)
  const connectingRef = useRef(false)
  const { toast } = useToast()

  const handleWebSocketMessage = useCallback(
    (message: WebSocketMessage) => {
      console.log("[v0] Processing WebSocket message:", message.type)

      switch (message.type) {
        case "connected":
          console.log("[v0] WebSocket connected with session:", message.session_id)
          setError(null)
          break

        case "typing":
          setIsTyping(true)
          break

        case "response_chunk":
          if (message.content) {
            setStreamingState((prev) => ({
              content: prev.content + message.content,
              isStreaming: true,
            }))
          }
          break

        case "response_complete":
          setIsTyping(false)
          if (message.content) {
            const assistantMessage: ChatMessage = {
              id: `msg-${Date.now()}`,
              role: "assistant",
              content: message.content,
              timestamp: message.timestamp,
              emotion: message.emotion,
              crisis_level: message.crisis_level,
              mode: message.mode,
              metadata: message.metadata,
            }

            setMessages((prev) => [...prev, assistantMessage])
            setStreamingState({
              content: "",
              isStreaming: false,
              metadata: {
                emotion: message.emotion,
                crisis_level: message.crisis_level,
                mode: message.mode,
                metadata: message.metadata,
              },
            })
          }
          break

        case "error":
          console.error("[v0] WebSocket error:", message.error)
          setError(message.error || "Unknown error")
          setIsTyping(false)
          setStreamingState({ content: "", isStreaming: false })

          if (message.error_code === "RATE_LIMIT_EXCEEDED") {
            toast({
              title: "Rate limit exceeded",
              description: "Please wait a moment before sending another message.",
              variant: "destructive",
            })
          }
          break

        case "pong":
          // Handle pong response if needed
          break
      }
    },
    [toast],
  )

  // Load older messages (prepend)
  const loadOlderMessages = useCallback(async () => {
    if (!sessionId) return
    if (historyLoading) return
    if (offset <= 0) return
    try {
      setHistoryLoading(true)
      const prevOffset = Math.max(0, offset - pageSize)
      const pageLimit = offset - prevOffset || pageSize
      const page = await apiClient.getSessionMessagesPaged(sessionId, prevOffset, pageLimit)
      const older = page.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.created_at,
        emotion: m.emotion,
        crisis_level: m.crisis_level,
        mode: m.mode,
        metadata: m.metadata,
      }))
      setMessages((prev) => [...older, ...prev])
      setOffset(prevOffset)
      setTotalMessages(page.total)
    } catch (err) {
      console.error("[v0] failed to load older messages:", err)
      setError(err instanceof Error ? err.message : "Failed to load older messages")
    } finally {
      setHistoryLoading(false)
    }
  }, [sessionId, historyLoading, offset, pageSize])

  const handleConnectionChange = useCallback((status: ConnectionStatus) => {
    setConnectionStatus(status)
    if (status === "connected") {
      setError(null)
    }
  }, [])

  const handleError = useCallback(
    (error: string) => {
      setError(error)
      toast({
        title: "Connection Error",
        description: error,
        variant: "destructive",
      })
    },
    [toast],
  )

  const connect = useCallback(async () => {
    try {
      if (connectingRef.current) {
        // Avoid parallel connects
        return
      }

      // Skip if already connected or connecting
      const status = wsClient.current?.getConnectionStatus()
      if (status === "connected" || status === "connecting") {
        return
      }

      connectingRef.current = true
      const accessToken = apiClient.isAuthenticated() ? localStorage.getItem("access_token") : null
      if (!accessToken) {
        throw new Error("No access token available")
      }

      if (wsClient.current) {
        wsClient.current.disconnect()
      }

      wsClient.current = new WebSocketClient(apiClient.getWebSocketUrl(), {
        onMessage: handleWebSocketMessage,
        onConnectionChange: handleConnectionChange,
        onError: handleError,
      })

      await wsClient.current.connect(accessToken, sessionId)
      connectingRef.current = false
    } catch (error) {
      console.error("[v0] Failed to connect WebSocket:", error)
      setError(error instanceof Error ? error.message : "Connection failed")
      connectingRef.current = false
    }
  }, [sessionId, handleWebSocketMessage, handleConnectionChange, handleError])

  // Load initial history when session changes
  useEffect(() => {
    const loadInitial = async () => {
      if (!sessionId) {
        setMessages([])
        setTotalMessages(0)
        setOffset(0)
        return
      }
      try {
        setHistoryLoading(true)
        // First page to discover total
        const first = await apiClient.getSessionMessagesPaged(sessionId, 0, pageSize)
        let startOffset = 0
        if (first.total > pageSize) {
          startOffset = first.total - pageSize
          const lastPage = await apiClient.getSessionMessagesPaged(sessionId, startOffset, pageSize)
          setMessages(
            lastPage.messages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: m.created_at,
              emotion: m.emotion,
              crisis_level: m.crisis_level,
              mode: m.mode,
              metadata: m.metadata,
            })),
          )
          setTotalMessages(lastPage.total)
          setOffset(startOffset)
        } else {
          setMessages(
            first.messages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: m.created_at,
              emotion: m.emotion,
              crisis_level: m.crisis_level,
              mode: m.mode,
              metadata: m.metadata,
            })),
          )
          setTotalMessages(first.total)
          setOffset(0)
        }
      } catch (err) {
        console.error("[v0] failed to load initial history:", err)
        setError(err instanceof Error ? err.message : "Failed to load history")
      } finally {
        setHistoryLoading(false)
      }
    }
    loadInitial()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const sendMessage = useCallback(
    async (content: string) => {
      try {
        // Connect on demand if needed
        if (!wsClient.current || connectionStatus !== "connected") {
          await connect()
        }

        if (!wsClient.current || wsClient.current.getConnectionStatus() !== "connected") {
          throw new Error("Unable to connect to chat service")
        }

        // Add user message immediately
        const userMessage = createChatMessage("user", content)

        setMessages((prev) => [...prev, userMessage])
        setError(null)

        // Send via WebSocket
        wsClient.current.sendChat(content)
      } catch (err) {
        console.error("[v0] sendMessage failed:", err)
        setError(err instanceof Error ? err.message : "Failed to send message")
      }
    },
    [connectionStatus, connect],
  )

  const disconnect = useCallback(() => {
    if (wsClient.current) {
      wsClient.current.disconnect()
      wsClient.current = null
    }
    connectingRef.current = false
    setConnectionStatus("disconnected")
  }, [])

  const getSessionId = useCallback(() => {
    return wsClient.current?.getSessionId() || sessionId
  }, [sessionId])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    messages,
    connectionStatus,
    isTyping,
    streamingState,
    error,
    connect,
    sendMessage,
    disconnect,
    getSessionId,
    // history
    loadOlderMessages,
    historyLoading,
    hasMoreHistory: offset > 0,
  }
}
