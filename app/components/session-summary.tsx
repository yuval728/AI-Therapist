"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { apiClient } from "@/lib/api"
import { Clock, MessageCircle, Brain, Target, AlertTriangle, Lightbulb, Loader2 } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface SessionSummaryData {
  session_id: string
  duration_minutes: number
  message_count: number
  primary_emotions?: string[]
  key_topics?: string[]
  insights?: string[]
  recommendations?: string[]
  crisis_level: number
  improvement_indicators?: string[]
}

interface SessionSummaryProps {
  sessionId: string | null
  messagesInitialized?: boolean
  delayMs?: number
}

export function SessionSummary({ sessionId, messagesInitialized = true, delayMs = 1000 }: SessionSummaryProps) {
  const [summary, setSummary] = useState<SessionSummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shouldLoad, setShouldLoad] = useState(false)
  const mountedRef = useRef(true)

  const loadSummary = useCallback(async () => {
    if (!sessionId || !mountedRef.current) return

    try {
      setLoading(true)
      setError(null)
      const summaryData = await apiClient.getSessionSummary(sessionId)
      if (mountedRef.current) {
        setSummary(summaryData as unknown as SessionSummaryData)
      }
    } catch (error) {
      if (mountedRef.current) {
        const errorMessage = error instanceof Error ? error.message : "Failed to load session summary"
        setError(errorMessage)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [sessionId])

  useEffect(() => {
    mountedRef.current = true

    return () => {
      mountedRef.current = false
    }
  }, [])

  // Delay loading until messages are initialized
  useEffect(() => {
    if (messagesInitialized && sessionId) {
      const timer = setTimeout(() => {
        if (mountedRef.current) {
          setShouldLoad(true)
        }
      }, delayMs)

      return () => clearTimeout(timer)
    } else {
      setShouldLoad(false)
      setSummary(null)
      setError(null)
    }
  }, [messagesInitialized, sessionId, delayMs])

  // Load summary when shouldLoad becomes true
  useEffect(() => {
    if (shouldLoad) {
      loadSummary()
    }
  }, [shouldLoad, loadSummary])

  const getEmotionColor = (emotion: string) => {
    const colors: Record<string, string> = {
      anxious: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
      sad: "bg-blue-500/10 text-blue-600 border-blue-500/20",
      happy: "bg-green-500/10 text-green-600 border-green-500/20",
      stressed: "bg-orange-500/10 text-orange-600 border-orange-500/20",
      confused: "bg-purple-500/10 text-purple-600 border-purple-500/20",
      hopeful: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
    }
    return colors[emotion.toLowerCase()] || "bg-gray-500/10 text-gray-600 border-gray-500/20"
  }

  const getCrisisLevelConfig = (level: number) => {
    if (level >= 4) {
      return { color: "text-red-600", bgColor: "bg-red-500/10", label: "High Priority" }
    } else if (level >= 2) {
      return { color: "text-yellow-600", bgColor: "bg-yellow-500/10", label: "Medium Priority" }
    } else {
      return { color: "text-green-600", bgColor: "bg-green-500/10", label: "Low Priority" }
    }
  }

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <Brain className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Select a session to view summary</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-primary" />
          <p className="text-sm text-muted-foreground">Loading session summary...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive" className="glass border-destructive/30">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <MessageCircle className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No summary available</p>
        </div>
      </div>
    )
  }

  const crisisConfig = getCrisisLevelConfig(summary.crisis_level)

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Session Overview */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" />
                Session Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Duration</p>
                  <p className="font-medium">{summary.duration_minutes} minutes</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Messages</p>
                  <p className="font-medium">{summary.message_count}</p>
                </div>
              </div>

              {summary.crisis_level > 0 && (
                <div className={cn("p-2 rounded-lg border", crisisConfig.bgColor)}>
                  <p className={cn("text-xs font-medium", crisisConfig.color)}>{crisisConfig.label}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Primary Emotions */}
        {(summary.primary_emotions?.length ?? 0) > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="glass border-border/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Primary Emotions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {(summary.primary_emotions ?? []).map((emotion, index) => (
                    <motion.div
                      key={emotion}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2 + index * 0.1 }}
                    >
                      <Badge variant="secondary" className={cn("text-xs", getEmotionColor(emotion))}>
                        {emotion}
                      </Badge>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Key Topics */}
        {(summary.key_topics?.length ?? 0) > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="glass border-border/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageCircle className="w-4 h-4 text-primary" />
                  Key Topics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(summary.key_topics ?? []).map((topic, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + index * 0.1 }}
                      className="flex items-center gap-2 text-sm"
                    >
                      <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                      <span className="text-foreground">{topic}</span>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Insights */}
        {(summary.insights?.length ?? 0) > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="glass border-border/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Brain className="w-4 h-4 text-primary" />
                  Insights
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(summary.insights ?? []).map((insight, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 + index * 0.1 }}
                      className="p-3 bg-primary/5 rounded-lg border border-primary/10"
                    >
                      <p className="text-xs text-foreground leading-relaxed">{insight}</p>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Recommendations */}
        {(summary.recommendations?.length ?? 0) > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card className="glass border-border/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-primary" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(summary.recommendations ?? []).map((recommendation, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Target className="w-3 h-3 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-foreground leading-relaxed">{recommendation}</span>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Improvement Indicators */}
        {(summary.improvement_indicators?.length ?? 0) > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <Card className="glass border-border/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Target className="w-4 h-4 text-green-600" />
                  Progress Indicators
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(summary.improvement_indicators ?? []).map((indicator, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + index * 0.1 }}
                      className="flex items-center gap-2 text-sm"
                    >
                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                      <span className="text-foreground">{indicator}</span>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </ScrollArea>
  )
}
