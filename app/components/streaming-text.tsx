"use client"

import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"

interface StreamingTextProps {
  content: string
  isStreaming: boolean
  onComplete?: () => void
  speed?: number
}

const DEFAULT_SPEED = 20

export function StreamingText({ 
  content, 
  isStreaming, 
  onComplete, 
  speed = DEFAULT_SPEED 
}: StreamingTextProps) {
  const [displayedContent, setDisplayedContent] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)

  const resetContent = useCallback(() => {
    setDisplayedContent("")
    setCurrentIndex(0)
  }, [])

  useEffect(() => {
    resetContent()
  }, [content, resetContent])

  useEffect(() => {
    if (isStreaming && currentIndex < content.length) {
      const timer = setTimeout(() => {
        setDisplayedContent(content.slice(0, currentIndex + 1))
        setCurrentIndex(prev => prev + 1)
      }, speed)

      return () => clearTimeout(timer)
    } else if (!isStreaming && content) {
      setDisplayedContent(content)
      setCurrentIndex(content.length)
      onComplete?.()
    }
  }, [content, currentIndex, isStreaming, onComplete, speed])

  return (
    <div className="text-sm leading-relaxed whitespace-pre-wrap">
      {displayedContent}
      {isStreaming && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ 
            duration: 0.8, 
            repeat: Infinity, 
            repeatType: "reverse" 
          }}
          className="inline-block w-2 h-4 bg-primary/60 ml-1"
        />
      )}
    </div>
  )
}
