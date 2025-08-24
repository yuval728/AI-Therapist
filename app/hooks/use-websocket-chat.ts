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
  }
}
