"use client"

import { useState, useCallback, useEffect } from "react"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
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

interface ApiChatOptions {
  autoCreateSession?: boolean
  onSessionCreated?: (sessionId: string) => void
}

type ConnectionState = "connected" | "connecting" | "disconnected" | "error"

export function useApiChat(sessionId?: string, options: ApiChatOptions = {}) {
  const { 
    autoCreateSession = true,
    onSessionCreated
  } = options

  const { toast } = useToast()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionState>("connected")
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(sessionId)
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<Error | null>(null)
  
  // Sync sessionId prop with internal state
  useEffect(() => {
    setCurrentSessionId(sessionId)
  }, [sessionId])
  
  // Use existing infinite messages hook for chat history
  const {
    messages,
    loading: messagesLoading,
    hasMore,
    loadMoreMessages,
    addMessage
  } = useInfiniteMessages(currentSessionId)

  // Send message function using the original apiClient
  const sendChatMessage = useCallback(async (
    content: string, 
    metadata?: Record<string, unknown>
  ) => {
    try {
      setIsSending(true)
      setSendError(null)
      setConnectionStatus("connecting")

      // Add user message immediately to UI
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
        metadata
      }
      addMessage(userMessage)

      // Send message using API client with session ID
      const response = await apiClient.sendMessage(content, currentSessionId, metadata)
      
      // Update session ID if it was created or changed
      if (response.sessionId && response.sessionId !== currentSessionId) {
        setCurrentSessionId(response.sessionId)
        onSessionCreated?.(response.sessionId)
      }
      
      // Add assistant response to UI
      const assistantMessage: ChatMessage = {
        id: response.messageId,
        role: "assistant", 
        content: response.reply,
        timestamp: new Date().toISOString()
      }
      addMessage(assistantMessage)

      setConnectionStatus("connected")
      
    } catch (error) {
      console.error("Failed to send message:", error)
      setSendError(error instanceof Error ? error : new Error("Failed to send message"))
      setConnectionStatus("error")
      
      toast({
        title: "Failed to send message",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive"
      })
    } finally {
      setIsSending(false)
    }
  }, [currentSessionId, addMessage, toast])

  return {
    messages,
    connectionStatus,
    isSending,
    sendError,
    messagesLoading,
    hasMore,
    loadMoreMessages,
    sendMessage: sendChatMessage,
    sessionId: currentSessionId
  }
}