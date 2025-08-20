"use client"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Brain, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { StreamingText } from "./streaming-text"

interface MessageBubbleProps {
  message: string
  sender: "user" | "therapist"
  timestamp: string
  isTyping?: boolean
  isStreaming?: boolean
  index?: number
}

export function MessageBubble({
  message,
  sender,
  timestamp,
  isTyping = false,
  isStreaming = false,
  index = 0,
}: MessageBubbleProps) {
  const isTherapist = sender === "therapist"

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.4,
        delay: index * 0.1,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={cn("flex gap-3 mb-6 group", isTherapist ? "justify-start" : "justify-end")}
    >
      {isTherapist && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: index * 0.1 + 0.2, duration: 0.3 }}
        >
          <Avatar className="w-8 h-8 border-2 border-primary/20 shadow-sm transition-all duration-300 group-hover:border-primary/40 group-hover:shadow-md">
            <AvatarFallback className="bg-gradient-to-br from-primary/10 to-primary/5 text-primary">
              <Brain className="w-4 h-4" />
            </AvatarFallback>
          </Avatar>
        </motion.div>
      )}

      <div className={cn("flex flex-col max-w-[80%] sm:max-w-[70%]", !isTherapist && "items-end")}>
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "px-4 py-3 rounded-2xl shadow-sm transition-all duration-300",
            "glass border border-border/30 backdrop-blur-md",
            "group-hover:shadow-lg group-hover:border-border/50",
            isTherapist
              ? "bg-gradient-to-br from-primary/8 to-primary/4 border-primary/20 text-card-foreground hover:from-primary/12 hover:to-primary/6"
              : "bg-gradient-to-br from-accent/8 to-accent/4 border-accent/20 text-card-foreground ml-auto hover:from-accent/12 hover:to-accent/6",
          )}
        >
          {isTyping ? (
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <motion.div
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 0.6, repeat: Number.POSITIVE_INFINITY, delay: 0 }}
                  className="w-2 h-2 bg-primary/60 rounded-full"
                />
                <motion.div
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 0.6, repeat: Number.POSITIVE_INFINITY, delay: 0.2 }}
                  className="w-2 h-2 bg-primary/60 rounded-full"
                />
                <motion.div
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 0.6, repeat: Number.POSITIVE_INFINITY, delay: 0.4 }}
                  className="w-2 h-2 bg-primary/60 rounded-full"
                />
              </div>
              <span className="text-xs text-muted-foreground ml-2">AI is thinking...</span>
            </div>
          ) : isStreaming ? (
            <StreamingText
              content={message}
              isStreaming={true}
              onComplete={() => {
                // Handle streaming completion if needed
              }}
            />
          ) : (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-sm leading-relaxed whitespace-pre-wrap"
            >
              {message}
            </motion.p>
          )}
        </motion.div>

        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-xs text-muted-foreground mt-1 px-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
        >
          {new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </motion.span>
      </div>

      {!isTherapist && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: index * 0.1 + 0.2, duration: 0.3 }}
        >
          <Avatar className="w-8 h-8 border-2 border-accent/20 shadow-sm transition-all duration-300 group-hover:border-accent/40 group-hover:shadow-md">
            <AvatarFallback className="bg-gradient-to-br from-accent/10 to-accent/5 text-accent">
              <User className="w-4 h-4" />
            </AvatarFallback>
          </Avatar>
        </motion.div>
      )}
    </motion.div>
  )
}
