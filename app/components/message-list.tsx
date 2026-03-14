"use client"
import { useEffect, useRef } from "react"
import { MessageBubble } from "./message-bubble"
import { motion } from "framer-motion"

interface ChatMessage {
  sender: "user" | "therapist"
  message: string
  timestamp: string
  isStreaming?: boolean
}

interface MessageListProps {
  messages: ChatMessage[]
  isTyping?: boolean
}

export function MessageList({ messages, isTyping = false }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="text-center max-w-md"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5, type: "spring", stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-primary/10 to-primary/5 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg"
          >
            <motion.svg
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.5, duration: 1.5 }}
              className="w-10 h-10 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <motion.path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </motion.svg>
          </motion.div>

          <motion.h3
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-xl font-manrope font-medium text-foreground mb-3"
          >
            Start your first conversation today
          </motion.h3>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-muted-foreground leading-relaxed"
          >
            I'm here to listen and support you. Share what's on your mind, and let's begin this journey together.
          </motion.p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
      <div className="max-w-4xl mx-auto">
        {messages.map((message, index) => (
          <MessageBubble
            key={`${message.timestamp}-${index}`}
            message={message.message}
            sender={message.sender}
            timestamp={message.timestamp}
            index={index}
            isStreaming={message.isStreaming}
          />
        ))}

        {isTyping && (
          <MessageBubble
            message=""
            sender="therapist"
            timestamp={new Date().toISOString()}
            isTyping={true}
            index={messages.length}
          />
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
