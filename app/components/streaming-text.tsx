"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"

interface StreamingTextProps {
  content: string
  isStreaming: boolean
  onComplete?: () => void
}

export function StreamingText({ content, isStreaming, onComplete }: StreamingTextProps) {
  const [displayedContent, setDisplayedContent] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (isStreaming && currentIndex < content.length) {
      const timer = setTimeout(() => {
        setDisplayedContent(content.slice(0, currentIndex + 1))
        setCurrentIndex(currentIndex + 1)
      }, 20) // Adjust speed as needed

      return () => clearTimeout(timer)
    } else if (!isStreaming) {
      setDisplayedContent(content)
      setCurrentIndex(content.length)
      if (content && onComplete) {
        onComplete()
      }
    }
  }, [content, currentIndex, isStreaming, onComplete])

  useEffect(() => {
    // Reset when content changes
    setDisplayedContent("")
    setCurrentIndex(0)
  }, [content])

  return (
    <div className="text-sm leading-relaxed whitespace-pre-wrap">
      {displayedContent}
      {isStreaming && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Number.POSITIVE_INFINITY, repeatType: "reverse" }}
          className="inline-block w-2 h-4 bg-primary/60 ml-1"
        />
      )}
    </div>
  )
}
