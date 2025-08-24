"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Plus, Search, MessageCircle, Calendar, Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { cn, formatDate, truncateText } from "@/lib/utils"
import type { TherapySession } from "@/lib/api"

interface SessionListProps {
  sessions: TherapySession[]
  activeSessionId: string | null
  loading: boolean
  hasMore: boolean
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  onLoadMore: () => void
  onSearch: (query: string) => TherapySession[]
}

export function SessionList({
  sessions,
  activeSessionId,
  loading,
  hasMore,
  onSessionSelect,
  onNewSession,
  onLoadMore,
  onSearch,
}: SessionListProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [filteredSessions, setFilteredSessions] = useState<TherapySession[]>(sessions)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  const updateFilteredSessions = useCallback(() => {
    const filtered = searchQuery ? onSearch(searchQuery) : sessions
    setFilteredSessions(filtered)
  }, [searchQuery, sessions, onSearch])

  useEffect(() => {
    updateFilteredSessions()
  }, [updateFilteredSessions])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          onLoadMore()
        }
      },
      { threshold: 0.1 },
    )

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current)
    }

    return () => observer.disconnect()
  }, [hasMore, loading, onLoadMore])

  const formatSessionDate = useCallback((dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    } else if (diffInHours < 24 * 7) {
      return date.toLocaleDateString([], { weekday: "short" })
    } else {
      return date.toLocaleDateString([], { month: "short", day: "numeric" })
    }
  }, [])

  const getEmotionColor = useCallback((emotion?: string) => {
    if (!emotion) return "bg-gray-500/10 text-gray-600"

    const emotionColors: Record<string, string> = {
      anxious: "bg-yellow-500/10 text-yellow-600",
      sad: "bg-blue-500/10 text-blue-600",
      angry: "bg-red-500/10 text-red-600",
      happy: "bg-green-500/10 text-green-600",
      stressed: "bg-orange-500/10 text-orange-600",
      confused: "bg-purple-500/10 text-purple-600",
    }

    return emotionColors[emotion.toLowerCase()] || "bg-gray-500/10 text-gray-600"
  }, [])

  return (
    <div className="flex flex-col h-full bg-background/50 backdrop-blur-sm border-r border-border/50">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-manrope font-semibold text-foreground">Sessions</h2>
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              onClick={onNewSession}
              size="sm"
              className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-primary-foreground shadow-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              New
            </Button>
          </motion.div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-9 glass border-border/50 focus:border-primary/50 transition-all duration-300"
          />
        </div>
      </div>

      {/* Session List */}
      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className="p-2">
          <AnimatePresence mode="popLayout">
            {filteredSessions.map((session, index) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <button
                  onClick={() => onSessionSelect(session.id)}
                  className={cn(
                    "w-full p-3 rounded-lg text-left transition-all duration-200 mb-2",
                    "glass border border-border/30 hover:border-border/50",
                    "hover:shadow-md hover:bg-accent/5",
                    activeSessionId === session.id ? "bg-primary/10 border-primary/30 shadow-sm" : "bg-background/30",
                  )}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <MessageCircle className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm font-medium text-foreground">
                        Session {filteredSessions.length - index}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="w-3 h-3" />
                      {formatSessionDate(session.created_at)}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {session.emotion && (
                      <Badge variant="secondary" className={cn("text-xs", getEmotionColor(session.emotion))}>
                        {session.emotion}
                      </Badge>
                    )}
                    {session.crisis_level && session.crisis_level > 0 && (
                      <Badge
                        variant="secondary"
                        className={cn(
                          "text-xs",
                          session.crisis_level >= 4
                            ? "bg-red-500/10 text-red-600"
                            : session.crisis_level >= 2
                              ? "bg-yellow-500/10 text-yellow-600"
                              : "bg-green-500/10 text-green-600",
                        )}
                      >
                        Level {session.crisis_level}
                      </Badge>
                    )}
                  </div>
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Load More Trigger */}
          {hasMore && (
            <div ref={loadMoreRef} className="flex justify-center py-4">
              {loading && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
            </div>
          )}

          {/* Empty State */}
          {filteredSessions.length === 0 && !loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-8 px-4">
              <MessageCircle className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground mb-2">
                {searchQuery ? "No sessions found" : "No sessions yet"}
              </p>
              {!searchQuery && (
                <p className="text-xs text-muted-foreground/70">Start your first conversation to create a session</p>
              )}
            </motion.div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
