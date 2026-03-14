"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { WebSocketClient, type WebSocketMessage, type ConnectionStatus } from "@/lib/websocket-client"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { handleWebSocketError } from "@/lib/error-handler"
import { useInfiniteMessages } from "@/hooks/use-infinite-messages"

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

interface StreamingState {
  content: string
  isStreaming: boolean
  metadata?: {
    emotion?: string
    crisis_level?: number
    mode?: string
    metadata?: Record<string, unknown>
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
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected")
  const [isTyping, setIsTyping] = useState(false)
  const [streamingState, setStreamingState] = useState<StreamingState>({
    content: "",
    isStreaming: false,
  })
  const [error, setError] = useState<string | null>(null)

  const wsClient = useRef<WebSocketClient | null>(null)
  const connectingRef = useRef(false)
  const mountedRef = useRef(true)
  const currentSessionRef = useRef<string | undefined>(sessionId)
  const { toast } = useToast()

  // Use infinite messages hook for message management
  const infiniteMessages = useInfiniteMessages(sessionId)

  // Update session ref when sessionId changes
  useEffect(() => {
    currentSessionRef.current = sessionId
  }, [sessionId])

  const handleWebSocketMessage = useCallback(
    (message: WebSocketMessage) => {
      if (!mountedRef.current) return

      switch (message.type) {
        case "connected":
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
              timestamp: message.timestamp || new Date().toISOString(),
              emotion: message.emotion,
              crisis_level: message.crisis_level,
              mode: message.mode,
              metadata: message.metadata,
            }

            // Add message to infinite messages
            infiniteMessages.addMessage(assistantMessage)
            
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
          setError(message.error || "Unknown error")
          setIsTyping(false)
          setStreamingState({ content: "", isStreaming: false })

          const wsError = new Error(message.error || "WebSocket error")
          handleWebSocketError(wsError, {
            component: "useWebSocketChat",
            action: "message_error",
            sessionId: currentSessionRef.current,
          })

          if (message.error_code === "RATE_LIMIT_EXCEEDED") {
            toast({
              title: "Rate limit exceeded",
              description: "Please wait a moment before sending another message.",
              variant: "destructive",
            })
          } else if (message.error_code === "SESSION_EXPIRED") {
            toast({
              title: "Session expired",
              description: "Please refresh the page to continue.",
              variant: "destructive",
            })
          } else {
            toast({
              title: "Connection Error",
              description: "There was a problem with the chat connection.",
              variant: "destructive",
            })
          }
          break

        case "pong":
          // Handle pong response if needed
          break
      }
    },
    [toast, infiniteMessages],
  )

  const handleConnectionChange = useCallback((status: ConnectionStatus) => {
    if (!mountedRef.current) return
    setConnectionStatus(status)
    if (status === "connected") {
      setError(null)
    }
  }, [])

  const handleError = useCallback(
    (error: string) => {
      if (!mountedRef.current) return
      setError(error)

      handleWebSocketError(new Error(error), {
        component: "useWebSocketChat",
        action: "connection_error",
        sessionId: currentSessionRef.current,
      })

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
        return
      }

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

      await wsClient.current.connect(accessToken, currentSessionRef.current)
      connectingRef.current = false
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Connection failed"
      setError(errorMessage)
      connectingRef.current = false

      if (error instanceof Error) {
        handleWebSocketError(error, {
          component: "useWebSocketChat",
          action: "connect_failed",
          sessionId: currentSessionRef.current,
        })
      }
    }
  }, [handleWebSocketMessage, handleConnectionChange, handleError])

  const sendMessage = useCallback(
    async (content: string) => {
      try {
        if (!wsClient.current || connectionStatus !== "connected") {
          await connect()
        }

        if (!wsClient.current || wsClient.current.getConnectionStatus() !== "connected") {
          throw new Error("Unable to connect to chat service")
        }

        const userMessage = createChatMessage("user", content)

        // Add user message to infinite messages
        infiniteMessages.addMessage(userMessage)
        setError(null)

        wsClient.current.sendChat(content)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message")
      }
    },
    [connectionStatus, connect, infiniteMessages],
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
    return wsClient.current?.getSessionId() || currentSessionRef.current
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false

      if (wsClient.current) {
        wsClient.current.disconnect()
        wsClient.current = null
      }
      connectingRef.current = false
    }
  }, [])

  return {
    messages: infiniteMessages.messages,
    connectionStatus,
    isTyping,
    streamingState,
    error: error || infiniteMessages.error,
    connect,
    sendMessage,
    disconnect,
    getSessionId,
    loadOlderMessages: infiniteMessages.loadMoreMessages,
    historyLoading: infiniteMessages.loadingMore,
    hasMoreHistory: infiniteMessages.hasMore,
    messagesLoading: infiniteMessages.loading,
    messagesInitialized: infiniteMessages.initialized,
  }
}
