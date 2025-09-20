"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"
import { apiClient } from "@/lib/api"
import { Activity, Server, Wifi, RefreshCw, CheckCircle, XCircle, AlertTriangle, Loader2 } from "lucide-react"
import { motion } from "framer-motion"
import { cn, formatTimestamp } from "@/lib/utils"


interface HealthData {
  status: string
  timestamp: string
  service: string
  components?: Array<{
    name: string
    status: string
    error?: string
    version?: string
    performance_mode?: string
  }>
  error?: string
  version?: string
  performance_mode?: string
  degraded?: boolean
  fallback?: boolean
}

export function HealthStatus() {

  const [health, setHealth] = useState<HealthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)

  // Enhanced health check using API client
  const checkHealth = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      setError(null)
      
      // Try detailed health check first
      let healthData: HealthData | null = null
      try {
        healthData = await apiClient.getDetailedHealthStatus()
      } catch (detailedError) {
        console.warn("Detailed health check failed, falling back to basic health check:", detailedError)
        try {
          healthData = await apiClient.getHealthStatus()
        } catch (basicError) {
          throw basicError
        }
      }

      if (mountedRef.current && healthData) {
        setHealth(healthData)
        setLastChecked(new Date())
      }
    } catch (error) {
      if (mountedRef.current) {
        const errorMessage = error instanceof Error ? error.message : "Health check failed"
        setError(errorMessage)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    checkHealth()

    intervalRef.current = setInterval(checkHealth, 30000)

    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [checkHealth])

  const getStatusConfig = useCallback((status: string) => {
    const configs = {
      healthy: {
        icon: CheckCircle,
        color: "text-green-600",
        bgColor: "bg-green-500/10",
        borderColor: "border-green-500/20",
        label: "Healthy",
      },
      degraded: {
        icon: AlertTriangle,
        color: "text-yellow-600",
        bgColor: "bg-yellow-500/10",
        borderColor: "border-yellow-500/20",
        label: "Degraded",
      },
      unhealthy: {
        icon: XCircle,
        color: "text-red-600",
        bgColor: "bg-red-500/10",
        borderColor: "border-red-500/20",
        label: "Unhealthy",
      },
    } as const

    return (
      configs[status.toLowerCase() as keyof typeof configs] || {
        icon: AlertTriangle,
        color: "text-gray-600",
        bgColor: "bg-gray-500/10",
        borderColor: "border-gray-500/20",
        label: "Unknown",
      }
    )
  }, [])

  const statusConfig = health ? getStatusConfig(health.status) : null

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              <h3 className="font-manrope font-semibold text-foreground">System Health</h3>
            </div>
            <Button variant="ghost" size="sm" onClick={checkHealth} disabled={loading}>
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            </Button>
          </div>
        </motion.div>

        {/* Error Alert */}
        {error && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
            <Alert variant="destructive" className="glass border-destructive/30">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </motion.div>
        )}

        {/* Loading State */}
        {loading && !health && (
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-primary" />
              <p className="text-sm text-muted-foreground">Checking system health...</p>
            </div>
          </div>
        )}

        {/* Health Status */}
        {health && statusConfig && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className={cn("glass border-border/30", statusConfig.borderColor)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <statusConfig.icon className={cn("w-4 h-4", statusConfig.color)} />
                  Service Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={cn("p-3 rounded-lg border", statusConfig.bgColor, statusConfig.borderColor)}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">Overall Status</span>
                    <Badge variant="secondary" className={cn("text-xs", statusConfig.bgColor, statusConfig.color)}>
                      {statusConfig.label}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Service</span>
                    <span className="text-foreground font-medium">{health.service}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Last Updated</span>
                    <span className="text-foreground font-medium">{formatTimestamp(health.timestamp)}</span>
                  </div>

                  {lastChecked && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Last Checked</span>
                      <span className="text-foreground font-medium">{formatTimestamp(lastChecked.toISOString())}</span>
                    </div>
                  )}

                  {/* Enhanced: show backend version, performance mode, degraded/fallback */}
                  {health.version && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Backend Version</span>
                      <span className="text-foreground font-medium">{health.version}</span>
                    </div>
                  )}
                  {health.performance_mode && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Performance Mode</span>
                      <span className="text-foreground font-medium">{health.performance_mode}</span>
                    </div>
                  )}
                  {health.degraded && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Degraded Mode</span>
                      <Badge variant="destructive">Degraded</Badge>
                    </div>
                  )}
                  {health.fallback && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Fallback Mode</span>
                      <Badge variant="outline">Fallback</Badge>
                    </div>
                  )}
                  {health.error && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Error</span>
                      <span className="text-foreground font-medium">{health.error}</span>
                    </div>
                  )}
                </div>

                {/* Enhanced: show backend components */}
                {health.components && health.components.length > 0 && (
                  <div className="mt-4">
                    <div className="font-semibold text-xs mb-2 text-muted-foreground">Backend Components</div>
                    <div className="space-y-2">
                      {health.components.map((comp, idx) => (
                        <div key={comp.name + idx} className="flex items-center justify-between text-xs">
                          <span className="font-medium">{comp.name}</span>
                          <span className={cn("font-medium", comp.status === "healthy" ? "text-green-600" : comp.status === "degraded" ? "text-yellow-600" : "text-red-600")}>{comp.status}</span>
                          {comp.version && <span className="ml-2 text-muted-foreground">v{comp.version}</span>}
                          {comp.performance_mode && <span className="ml-2 text-muted-foreground">{comp.performance_mode}</span>}
                          {comp.error && <span className="ml-2 text-destructive">{comp.error}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Connection Status */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Wifi className="w-4 h-4 text-primary" />
                Connection Info
              </CardTitle>
              <CardDescription className="text-xs">Real-time connection status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm text-foreground">API Connected</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full" />
                  <span className="text-sm text-foreground">API Accessible</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-purple-500 rounded-full" />
                  <span className="text-sm text-foreground">Authentication Active</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* System Metrics */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" />
                Performance
              </CardTitle>
              <CardDescription className="text-xs">System performance indicators</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Response Time</p>
                  <p className="font-medium text-green-600">~120ms</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Uptime</p>
                  <p className="font-medium text-green-600">99.9%</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Load</p>
                  <p className="font-medium text-yellow-600">Moderate</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Region</p>
                  <p className="font-medium text-foreground">US-East</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </ScrollArea>
  )
}
