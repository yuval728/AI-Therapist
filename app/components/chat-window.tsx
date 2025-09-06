"use client"
import { useState, useEffect, useCallback, useRef, useMemo } from "react"
import { MessageList } from "./message-list"
import { MessageInput } from "./message-input"
import { ChatNavbar } from "./chat-navbar"
import { DemoBanner } from "./demo-banner"
import { apiClient } from "@/lib/api"
import { useRouter } from "next/navigation"
import { useToast } from "@/hooks/use-toast"

interface ChatMessage {
  sender: "user" | "therapist"
  message: string
  timestamp: string
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isTyping, setIsTyping] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)
  const router = useRouter()
  const { toast } = useToast()

  const loadChatHistory = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      setError(null)
      const history = await apiClient.getChatHistory()
      if (mountedRef.current) {
        setMessages(history)
      }
    } catch (err) {
      console.error("Failed to load chat history:", err)
      if (err instanceof Error && err.message === "Session expired") {
        handleLogout()
        return
      }
      if (mountedRef.current) {
        setError("Failed to load chat history")
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false)
      }
    }
  }, []) // Removed dependencies to prevent infinite loops

  const handleLogout = useCallback(() => {
    apiClient.logout()
    toast({
      title: "Logged out",
      description: "You have been successfully logged out.",
    })
    router.push("/auth")
  }, [toast, router])

  const handleRetry = useCallback(() => {
    setIsLoading(true)
    loadChatHistory()
  }, [loadChatHistory])

  useEffect(() => {
    mountedRef.current = true
    loadChatHistory()

    return () => {
      mountedRef.current = false
    }
  }, [loadChatHistory])

  const createMessage = useCallback(
    (sender: "user" | "therapist", message: string): ChatMessage => ({
      sender,
      message,
      timestamp: new Date().toISOString(),
    }),
    [],
  )

  const handleSendMessage = useCallback(
    async (messageText: string) => {
      const userMessage = createMessage("user", messageText)
      setMessages((prev) => [...prev, userMessage])
      setIsTyping(true)
      setError(null)

      try {
        const response = await apiClient.sendMessage(messageText)
        const therapistMessage = createMessage("therapist", response.reply)
        if (mountedRef.current) {
          setMessages((prev) => [...prev, therapistMessage])
        }
      } catch (err) {
        console.error("Failed to send message:", err)
        if (err instanceof Error && err.message === "Session expired") {
          handleLogout()
          return
        }

        const errorMessage = createMessage(
          "therapist",
          "I apologize, but I'm having trouble responding right now. Please try again in a moment.",
        )
        if (mountedRef.current) {
          setMessages((prev) => [...prev, errorMessage])
          setError("Failed to send message")
        }
      } finally {
        if (mountedRef.current) {
          setIsTyping(false)
        }
      }
    },
    [createMessage, handleLogout],
  )

  const loadingState = useMemo(
    () => (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-secondary/20">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading your conversation...</p>
        </div>
      </div>
    ),
    [],
  )

  const errorState = useMemo(
    () => (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-secondary/20">
        <div className="text-center max-w-md p-6">
          <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-destructive"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-manrope font-medium text-foreground mb-2">Something went wrong</h3>
          <p className="text-muted-foreground text-sm mb-4">{error}</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    ),
    [error, handleRetry, handleLogout],
  )

  if (isLoading) {
    return loadingState
  }

  if (error && messages.length === 0) {
    return errorState
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-background via-background to-secondary/20">
      <ChatNavbar onLogout={handleLogout} />

      <div className="flex-1 flex flex-col">
        {apiClient.isDemoMode() && (
          <div className="px-4 pt-4">
            <DemoBanner />
          </div>
        )}

        <MessageList messages={messages} isTyping={isTyping} />
      </div>

      <MessageInput onSendMessage={handleSendMessage} disabled={isTyping} />
    </div>
  )
}
