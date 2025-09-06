"use client"
import { useEffect, useRef, useCallback, useState } from "react"
import type React from "react"

import { MessageBubble } from "./message-bubble"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowDown } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

interface ChatMessage {
  sender: "user" | "therapist"
  message: string
  timestamp: string
  isStreaming?: boolean
}

interface MessageListProps {
  messages: ChatMessage[]
  isTyping?: boolean
  onLoadMore?: () => void
  hasMore?: boolean
  isLoadingMore?: boolean
  loading?: boolean
}

export function MessageList({
  messages,
  isTyping = false,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  loading = false,
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [isNearBottom, setIsNearBottom] = useState(true)
  const previousMessageCount = useRef(messages.length)
  const lastScrollTop = useRef(0)
  const isLoadingMoreRef = useRef(false)

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }, [])

  // Check if user is near bottom of scroll area
  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight
      const nearBottom = distanceFromBottom < 100
      const nearTop = scrollTop < 200

      setIsNearBottom(nearBottom)
      setShouldAutoScroll(nearBottom)

      // Load more messages when scrolling near the top
      if (nearTop && hasMore && !isLoadingMoreRef.current && onLoadMore) {
        isLoadingMoreRef.current = true
        const previousScrollHeight = scrollHeight
        
        onLoadMore()
        
        // Maintain scroll position after loading more messages
        setTimeout(() => {
          if (containerRef.current) {
            const newScrollHeight = containerRef.current.scrollHeight
            const heightDifference = newScrollHeight - previousScrollHeight
            containerRef.current.scrollTop = scrollTop + heightDifference
          }
          isLoadingMoreRef.current = false
        }, 100)
      }

      lastScrollTop.current = scrollTop
    },
    [hasMore, onLoadMore],
  )

  // Auto-scroll for new messages only if user is near bottom
  useEffect(() => {
    const messageCountIncreased = messages.length > previousMessageCount.current
    previousMessageCount.current = messages.length

    if (messageCountIncreased && shouldAutoScroll) {
      // Small delay to ensure DOM is updated
      setTimeout(() => scrollToBottom(), 50)
    }
  }, [messages.length, shouldAutoScroll, scrollToBottom])

  // Auto-scroll when typing indicator appears/disappears
  useEffect(() => {
    if (isTyping && shouldAutoScroll) {
      setTimeout(() => scrollToBottom(), 50)
    }
  }, [isTyping, shouldAutoScroll, scrollToBottom])

  // Scroll to bottom on initial load
  useEffect(() => {
    if (messages.length > 0 && !loading) {
      scrollToBottom("auto")
    }
  }, [loading, scrollToBottom]) // Run when loading completes

  // Handle loading state
  if (loading && messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading messages...</p>
        </motion.div>
      </div>
    )
  }

  if (messages.length === 0 && !isTyping && !loading) {
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
    <div className="flex-1 flex flex-col overflow-hidden relative">
      <ScrollArea 
        ref={scrollAreaRef} 
        className="flex-1 px-4 py-6" 
        onScrollCapture={handleScroll}
      >
        <div className="max-w-4xl mx-auto" ref={containerRef}>
          {/* Load more button at top */}
          <AnimatePresence>
            {hasMore && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex justify-center mb-4"
              >
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isLoadingMore}
                  onClick={onLoadMore}
                  className="bg-background/80 backdrop-blur-sm shadow-sm hover:shadow-md transition-shadow"
                >
                  {isLoadingMore ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Loading older messages...
                    </>
                  ) : (
                    <>
                      <ArrowDown className="w-4 h-4 mr-2 rotate-180" />
                      Load older messages
                    </>
                  )}
                </Button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages */}
          <div className="space-y-4">
            {messages.map((message, index) => (
              <motion.div
                key={`${message.timestamp}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ 
                  duration: 0.3, 
                  delay: index < 10 ? index * 0.05 : 0 // Only animate first 10 messages
                }}
              >
                <MessageBubble
                  message={message.message}
                  sender={message.sender}
                  timestamp={message.timestamp}
                  index={index}
                  isStreaming={message.isStreaming}
                />
              </motion.div>
            ))}
          </div>

          {/* Typing indicator */}
          <AnimatePresence>
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <MessageBubble
                  message=""
                  sender="therapist"
                  timestamp={new Date().toISOString()}
                  isTyping={true}
                  index={messages.length}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Scroll to bottom button */}
      <AnimatePresence>
        {!isNearBottom && messages.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.8 }}
            className="absolute bottom-4 right-4 z-10"
          >
            <Button
              size="sm"
              variant="secondary"
              onClick={() => scrollToBottom()}
              className="rounded-full shadow-lg bg-background/90 backdrop-blur-sm border hover:shadow-xl transition-all duration-200"
            >
              <ArrowDown className="w-4 h-4" />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
