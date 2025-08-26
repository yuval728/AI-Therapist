"use client"

import { MessageList } from "./message-list"
import { MessageInput } from "./message-input"
import { SessionMetadata } from "./session-metadata"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"
import type { ConnectionStatus } from "@/lib/websocket-client"
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

interface ChatAreaProps {
  messages: ChatMessage[]
  isTyping: boolean
  streamingState: StreamingState
  onSendMessage: (content: string) => Promise<void>
  connectionStatus: ConnectionStatus
  error: string | null
  activeSession: TherapySession | null
  // Pagination controls
  onLoadOlder?: () => Promise<void> | void
  hasMoreHistory?: boolean
  historyLoading?: boolean
}

export function ChatArea({
  messages,
  isTyping,
  streamingState,
  onSendMessage,
  connectionStatus,
  error,
  activeSession,
  onLoadOlder,
  hasMoreHistory,
  historyLoading,
}: ChatAreaProps) {
  const isConnected = connectionStatus === "connected"
  // Allow typing even when disconnected; sendMessage will lazy-connect
  const isDisabled = isTyping

  // Convert messages to the format expected by MessageList
  type DisplayMessage = { sender: "user" | "therapist"; message: string; timestamp: string; isStreaming?: boolean }
  const formattedMessages: DisplayMessage[] = messages.map((msg) => ({
    sender: msg.role === "user" ? ("user" as const) : ("therapist" as const),
    message: msg.content,
    timestamp: msg.timestamp,
  }))

  const allMessages: DisplayMessage[] = [...formattedMessages]
  if (streamingState.isStreaming && streamingState.content) {
    allMessages.push({
      sender: "therapist" as const,
      message: streamingState.content,
      timestamp: new Date().toISOString(),
      isStreaming: true,
    })
  }

  const handleRetry = () => {
    // Trigger reconnection logic
    window.location.reload()
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
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
      <div className="flex-1 overflow-hidden">
        <div className="px-4 pt-4">
          {hasMoreHistory && (
            <Button
              variant="outline"
              size="sm"
              disabled={historyLoading}
              onClick={() => onLoadOlder && onLoadOlder()}
              className="w-full mb-2"
            >
              {historyLoading ? "Loading..." : "Load older messages"}
            </Button>
          )}
        </div>
        <MessageList messages={allMessages} isTyping={isTyping && !streamingState.isStreaming} />
      </div>

      {/* Session Metadata */}
      {streamingState.metadata && (
        <div className="px-4">
          <SessionMetadata
            emotion={streamingState.metadata.emotion}
            crisis_level={streamingState.metadata.crisis_level}
            mode={streamingState.metadata.mode}
            metadata={streamingState.metadata.metadata}
            timestamp={new Date().toISOString()}
          />
        </div>
      )}

      {/* Message Input */}
      <MessageInput
        onSendMessage={onSendMessage}
        disabled={isDisabled}
        placeholder={
          !isConnected
            ? "Type your message to start the chat"
            : isTyping
              ? "AI is responding..."
              : "How are you feeling today?"
        }
      />
    </div>
  )
}
