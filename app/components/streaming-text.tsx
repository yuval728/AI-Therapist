"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { motion } from "framer-motion"

interface StreamingTextProps {
  content: string
  isStreaming: boolean
  onComplete?: () => void
  speed?: number
}

const DEFAULT_SPEED = 20

export function StreamingText({ content, isStreaming, onComplete, speed = DEFAULT_SPEED }: StreamingTextProps) {
  const [displayedContent, setDisplayedContent] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)

  const resetContent = useCallback(() => {
    setDisplayedContent("")
    setCurrentIndex(0)
  }, [])

  useEffect(() => {
    mountedRef.current = true
    resetContent()

    return () => {
      mountedRef.current = false
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [content, resetContent])

  useEffect(() => {
    // Clear any existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }

    if (isStreaming && currentIndex < content.length && mountedRef.current) {
      timerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          setDisplayedContent(content.slice(0, currentIndex + 1))
          setCurrentIndex((prev) => prev + 1)
        }
      }, speed)
    } else if (!isStreaming && content && mountedRef.current) {
      setDisplayedContent(content)
      setCurrentIndex(content.length)
      onComplete?.()
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
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
            repeat: Number.POSITIVE_INFINITY,
            repeatType: "reverse",
          }}
          className="inline-block w-2 h-4 bg-primary/60 ml-1"
        />
      )}
    </div>
  )
}
