"use client"

import { useEffect, useState } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, BarChart2, TrendingUp, Clock, AlertTriangle } from "lucide-react"

interface Metric {
  name: string
  value: string | number
  unit?: string
  description?: string
}

interface MetricsData {
  metrics: Metric[]
  timestamp: string
  history?: Array<{ timestamp: string; metrics: Metric[] }>
  error?: string
}

export function MetricsDashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchMetrics() {
      setLoading(true)
      setError(null)
      let data = null
      try {
        // Try /api/health/metrics first
        let response = await fetch("/api/health/metrics")
        if (response.ok) {
          data = await response.json()
        } else {
          // Try /health/metrics
          response = await fetch("/health/metrics")
          if (response.ok) {
            data = await response.json()
          }
        }
        if (!data) throw new Error("Failed to fetch metrics")
        setMetrics(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch metrics")
      } finally {
        setLoading(false)
      }
    }
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-primary" />
              System Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-primary" />
                <p className="text-sm text-muted-foreground">Loading metrics...</p>
              </div>
            )}
            {error && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}
            {metrics && metrics.metrics && (
              <div className="grid grid-cols-2 gap-4">
                {metrics.metrics.map((metric, idx) => (
                  <div key={metric.name + idx} className="p-2 border rounded-lg bg-muted/10">
                    <div className="font-semibold text-xs text-muted-foreground">{metric.name}</div>
                    <div className="text-lg font-bold text-foreground">{metric.value} {metric.unit}</div>
                    {metric.description && <div className="text-xs text-muted-foreground">{metric.description}</div>}
                  </div>
                ))}
              </div>
            )}
            {metrics && metrics.history && metrics.history.length > 0 && (
              <div className="mt-6">
                <div className="font-semibold text-xs mb-2 text-muted-foreground flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Metrics History
                </div>
                <div className="space-y-2">
                  {metrics.history.map((entry, idx) => (
                    <div key={entry.timestamp + idx} className="flex items-center gap-4 text-xs">
                      <span className="text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</span>
                      <span className="font-medium">{entry.metrics.map(m => `${m.name}: ${m.value}${m.unit ? ' ' + m.unit : ''}`).join(", ")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}
