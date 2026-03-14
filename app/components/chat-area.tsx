"use client"

import { MessageList } from "./message-list"
import { MessageInput } from "./message-input"
import { SessionMetadata } from "./session-metadata"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"
import type { TherapySession } from "@/lib/api"

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


interface ChatAreaProps {
  messages: ChatMessage[]
  isTyping: boolean
  onSendMessage: (content: string) => Promise<void>
  error: string | null
  activeSession: TherapySession | null
  // Pagination controls
  onLoadOlder?: () => Promise<void> | void
  hasMoreHistory?: boolean
  historyLoading?: boolean
  // New props for improved loading
  messagesLoading?: boolean
  messagesInitialized?: boolean
}

export function ChatArea({
  messages,
  isTyping,
  onSendMessage,
  error,
  activeSession,
  onLoadOlder,
  hasMoreHistory,
  historyLoading,
  messagesLoading,
  messagesInitialized,
}: ChatAreaProps) {
  const isDisabled = isTyping

  // Convert messages to the format expected by MessageList
  type DisplayMessage = { sender: "user" | "therapist"; message: string; timestamp: string }
  const formattedMessages: DisplayMessage[] = messages.map((msg) => ({
    sender: msg.role === "user" ? ("user" as const) : ("therapist" as const),
    message: msg.content,
    timestamp: msg.timestamp,
  }))


  const handleRetry = () => {
    // Trigger reconnection logic
    window.location.reload()
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Error Alert */}
      {error && (
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mx-4 mt-4">
          <Alert variant="destructive" className="glass border-destructive/30">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button variant="outline" size="sm" onClick={handleRetry} className="ml-2 bg-transparent">
                <RefreshCw className="w-4 h-4 mr-1" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </motion.div>
      )}

      {/* Messages with Load Older */}
      <MessageList 
        messages={formattedMessages} 
        isTyping={isTyping}
        onLoadMore={onLoadOlder}
        hasMore={hasMoreHistory}
        isLoadingMore={historyLoading}
        loading={messagesLoading}
      />

      {/* Session Metadata - Show from active session */}
      {activeSession && (
        <div className="px-4">
          <SessionMetadata
              emotion={activeSession.emotion}
            crisis_level={activeSession.crisis_level}
              mode="therapy"
            metadata={activeSession.metadata}
            timestamp={activeSession.updated_at}
          />
        </div>
      )}

      {/* Message Input */}
      <MessageInput
        onSendMessage={onSendMessage}
        disabled={isDisabled}
        placeholder={
          isTyping
            ? "AI is responding..."
            : "How are you feeling today?"
        }
      />
    </div>
  )
}
