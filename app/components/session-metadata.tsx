"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Heart, AlertTriangle, Brain, Clock } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface SessionMetadataProps {
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, any>
  timestamp: string
}

export function SessionMetadata({ emotion, crisis_level, mode, metadata, timestamp }: SessionMetadataProps) {
  const getEmotionIcon = (emotion?: string) => {
    switch (emotion?.toLowerCase()) {
      case "happy":
      case "joy":
        return "😊"
      case "sad":
      case "sadness":
        return "😢"
      case "angry":
      case "anger":
        return "😠"
      case "anxious":
      case "anxiety":
        return "😰"
      case "stressed":
      case "stress":
        return "😤"
      case "confused":
        return "😕"
      default:
        return "💭"
    }
  }

  const getCrisisLevelConfig = (level?: number) => {
    if (!level || level === 0) return null

    if (level >= 4) {
      return {
        color: "text-red-600",
        bgColor: "bg-red-500/10",
        icon: AlertTriangle,
        label: "High",
      }
    } else if (level >= 2) {
      return {
        color: "text-yellow-600",
        bgColor: "bg-yellow-500/10",
        icon: AlertTriangle,
        label: "Medium",
      }
    } else {
      return {
        color: "text-green-600",
        bgColor: "bg-green-500/10",
        icon: Heart,
        label: "Low",
      }
    }
  }

  const crisisConfig = getCrisisLevelConfig(crisis_level)

  if (!emotion && !crisis_level && !mode && !metadata) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="my-4"
    >
      <Card className="glass border-border/30 bg-background/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-foreground">Session Insights</span>
            <div className="flex items-center gap-1 text-xs text-muted-foreground ml-auto">
              <Clock className="w-3 h-3" />
              {new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {emotion && (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.1 }}>
                <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                  <span className="mr-1">{getEmotionIcon(emotion)}</span>
                  {emotion}
                </Badge>
              </motion.div>
            )}

            {crisisConfig && (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2 }}>
                <Badge variant="secondary" className={cn(crisisConfig.bgColor, crisisConfig.color)}>
                  <crisisConfig.icon className="w-3 h-3 mr-1" />
                  {crisisConfig.label} Priority
                </Badge>
              </motion.div>
            )}

            {mode && (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.3 }}>
                <Badge variant="secondary" className="bg-accent/10 text-accent">
                  {mode}
                </Badge>
              </motion.div>
            )}

            {metadata?.topics && Array.isArray(metadata.topics) && (
              <>
                {metadata.topics.slice(0, 3).map((topic: string, index: number) => (
                  <motion.div
                    key={topic}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                  >
                    <Badge variant="outline" className="text-xs">
                      {topic}
                    </Badge>
                  </motion.div>
                ))}
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
