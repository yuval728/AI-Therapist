"use client"

import type React from "react"
import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface MessageInputProps {
  onSendMessage: (message: string) => Promise<void>
  disabled?: boolean
  placeholder?: string
}

export function MessageInput({
  onSendMessage,
  disabled = false,
  placeholder = "How are you feeling today?",
}: MessageInputProps) {
  const [message, setMessage] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [isFocused, setIsFocused] = useState(false)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isSending || disabled) return

    const messageToSend = message.trim()
    setMessage("")
    setIsSending(true)

    try {
      await onSendMessage(messageToSend)
    } catch (error) {
      console.error("Failed to send message:", error)
      setMessage(messageToSend)
    } finally {
      setIsSending(false)
    }
  }, [message, isSending, disabled, onSendMessage])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }, [handleSubmit])

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="sticky bottom-0 bg-background/80 backdrop-blur-xl border-t border-border/50 p-4"
    >
      <div className="max-w-4xl mx-auto">
        <motion.form onSubmit={handleSubmit} animate={{ scale: isFocused ? 1.02 : 1 }} transition={{ duration: 0.2 }}>
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder}
                disabled={disabled || isSending}
                className={cn(
                  "min-h-[52px] max-h-32 resize-none rounded-2xl",
                  "glass border-border/50 focus:border-primary/50 backdrop-blur-md",
                  "placeholder:text-muted-foreground/70",
                  "transition-all duration-300 focus:shadow-lg focus:shadow-primary/10",
                  "pr-12", // Space for send button
                )}
                rows={1}
              />

              {/* Floating label effect */}
              <motion.div
                initial={false}
                animate={{
                  scale: message || isFocused ? 0.8 : 1,
                  y: message || isFocused ? -24 : 0,
                  opacity: message || isFocused ? 0.7 : 0,
                }}
                transition={{ duration: 0.2 }}
                className="absolute left-3 top-3 text-sm text-muted-foreground pointer-events-none"
              >
                {placeholder}
              </motion.div>
            </div>

            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} transition={{ duration: 0.1 }}>
              <Button
                type="submit"
                size="icon"
                disabled={!message.trim() || isSending || disabled}
                className={cn(
                  "h-12 w-12 rounded-2xl shrink-0 relative overflow-hidden",
                  "bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70",
                  "text-primary-foreground shadow-lg hover:shadow-xl",
                  "transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed",
                  "before:absolute before:inset-0 before:bg-gradient-to-r before:from-white/20 before:to-transparent before:opacity-0 hover:before:opacity-100 before:transition-opacity before:duration-300",
                )}
              >
                <motion.div
                  animate={{ rotate: isSending ? 360 : 0 }}
                  transition={{ duration: isSending ? 1 : 0.3, repeat: isSending ? Infinity : 0 }}
                >
                  {isSending ? <Loader2 className="h-4 w-4" /> : <Send className="h-4 w-4" />}
                </motion.div>
              </Button>
            </motion.div>
          </div>
        </motion.form>
      </div>
    </motion.div>
  )
}
