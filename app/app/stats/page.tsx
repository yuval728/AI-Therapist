"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { RouteGuard } from "@/components/route-guard"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { ArrowLeft, MessageCircle, Clock, TrendingUp, Calendar, Target, Heart, BarChart3, Loader2 } from "lucide-react"
import { motion } from "framer-motion"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"

interface UserStats {
  total_sessions: number
  total_messages: number
  avg_session_duration: number
  most_common_emotion: string
  improvement_score: number
  streak_days: number
  last_session: string
  weekly_sessions: number[]
  emotion_distribution: Record<string, number>
}

export default function StatsPage() {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { toast } = useToast()
  const router = useRouter()

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setError(null)
      const userStats = await apiClient.getUserStats()
      setStats(userStats as UserStats)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to load stats"
      setError(errorMessage)
      if (errorMessage === "Session expired") {
        router.push("/auth")
      }
    } finally {
      setLoading(false)
    }
  }

  const getEmotionColor = (emotion: string) => {
    const colors: Record<string, string> = {
      anxious: "bg-yellow-500/10 text-yellow-600",
      sad: "bg-blue-500/10 text-blue-600",
      happy: "bg-green-500/10 text-green-600",
      stressed: "bg-orange-500/10 text-orange-600",
      confused: "bg-purple-500/10 text-purple-600",
    }
    return colors[emotion.toLowerCase()] || "bg-gray-500/10 text-gray-600"
  }

  const getImprovementColor = (score: number) => {
    if (score >= 8) return "text-green-600"
    if (score >= 6) return "text-yellow-600"
    return "text-orange-600"
  }

  if (loading) {
    return (
      <RouteGuard requireAuth={true}>
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-secondary/20">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-muted-foreground">Loading your statistics...</p>
          </div>
        </div>
      </RouteGuard>
    )
  }

  return (
    <RouteGuard requireAuth={true}>
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-secondary/20 p-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-4 mb-8"
          >
            <Button variant="ghost" onClick={() => router.back()} className="p-2">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-manrope font-bold text-foreground">Your Progress</h1>
              <p className="text-muted-foreground">Track your mental health journey</p>
            </div>
          </motion.div>

          {/* Error Alert */}
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
              <Alert variant="destructive" className="glass border-destructive/30">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </motion.div>
          )}

          {stats && (
            <div className="grid gap-6">
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                  <Card className="glass border-border/30 shadow-sm">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                          <MessageCircle className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-foreground">{stats.total_sessions}</p>
                          <p className="text-sm text-muted-foreground">Total Sessions</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                  <Card className="glass border-border/30 shadow-sm">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-500/10 rounded-full flex items-center justify-center">
                          <Clock className="w-5 h-5 text-green-600" />
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-foreground">{stats.avg_session_duration}m</p>
                          <p className="text-sm text-muted-foreground">Avg Duration</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                  <Card className="glass border-border/30 shadow-sm">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-500/10 rounded-full flex items-center justify-center">
                          <Target className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-foreground">{stats.streak_days}</p>
                          <p className="text-sm text-muted-foreground">Day Streak</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                  <Card className="glass border-border/30 shadow-sm">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-orange-500/10 rounded-full flex items-center justify-center">
                          <TrendingUp className="w-5 h-5 text-orange-600" />
                        </div>
                        <div>
                          <p className={`text-2xl font-bold ${getImprovementColor(stats.improvement_score)}`}>
                            {stats.improvement_score}/10
                          </p>
                          <p className="text-sm text-muted-foreground">Progress Score</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* Emotion Distribution */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
                <Card className="glass border-border/30 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Heart className="w-5 h-5 text-primary" />
                      Emotion Patterns
                    </CardTitle>
                    <CardDescription>Your most common emotional states during sessions</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {Object.entries(stats.emotion_distribution)
                        .sort(([, a], [, b]) => b - a)
                        .map(([emotion, percentage], index) => (
                          <motion.div
                            key={emotion}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.6 + index * 0.1 }}
                            className="flex items-center justify-between"
                          >
                            <div className="flex items-center gap-3">
                              <Badge className={getEmotionColor(emotion)}>{emotion}</Badge>
                              <span className="text-sm text-muted-foreground">{percentage}%</span>
                            </div>
                            <div className="flex-1 mx-4">
                              <div className="w-full bg-secondary/30 rounded-full h-2">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${percentage}%` }}
                                  transition={{ delay: 0.8 + index * 0.1, duration: 0.8 }}
                                  className="bg-primary h-2 rounded-full"
                                />
                              </div>
                            </div>
                          </motion.div>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Weekly Activity */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
                <Card className="glass border-border/30 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-primary" />
                      Weekly Activity
                    </CardTitle>
                    <CardDescription>Your session frequency over the past week</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-end justify-between gap-2 h-32">
                      {stats.weekly_sessions.map((sessions, index) => {
                        const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        const maxSessions = Math.max(...stats.weekly_sessions, 1)
                        const height = (sessions / maxSessions) * 100

                        return (
                          <motion.div
                            key={index}
                            initial={{ height: 0 }}
                            animate={{ height: `${height}%` }}
                            transition={{ delay: 0.8 + index * 0.1, duration: 0.6 }}
                            className="flex-1 flex flex-col items-center gap-2"
                          >
                            <div className="w-full bg-primary/20 rounded-t flex items-end justify-center min-h-[20px]">
                              {sessions > 0 && (
                                <span className="text-xs font-medium text-primary mb-1">{sessions}</span>
                              )}
                            </div>
                            <span className="text-xs text-muted-foreground">{days[index]}</span>
                          </motion.div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Recent Activity */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}>
                <Card className="glass border-border/30 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="w-5 h-5 text-primary" />
                      Recent Activity
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-3 text-sm">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-muted-foreground">Last session:</span>
                      <span className="text-foreground font-medium">
                        {new Date(stats.last_session).toLocaleString()}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          )}
        </div>
      </div>
    </RouteGuard>
  )
}
