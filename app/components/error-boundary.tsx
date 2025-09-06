"use client"

import type React from "react"
import { Component, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, RefreshCw, Home } from "lucide-react"
import { errorHandler } from "@/lib/error-handler"

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  level?: "app" | "page" | "component"
}

interface State {
  hasError: boolean
  error: Error | null
  errorId: string | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorId: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const { level = "component", onError } = this.props

    // Log error with context
    errorHandler.logError(
      error,
      {
        component: `ErrorBoundary-${level}`,
        action: "component_error",
        timestamp: new Date().toISOString(),
      },
      level === "app" ? "critical" : level === "page" ? "high" : "medium",
      "ui",
    )

    // Call custom error handler if provided
    onError?.(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorId: null })
  }

  handleGoHome = () => {
    if (typeof window !== "undefined") {
      window.location.href = "/"
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      const { level = "component" } = this.props
      const isAppLevel = level === "app"

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-secondary/20">
          <Card className="w-full max-w-md glass border-destructive/30 shadow-lg">
            <CardHeader className="text-center">
              <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-8 h-8 text-destructive" />
              </div>
              <CardTitle className="text-xl text-foreground">
                {isAppLevel ? "Application Error" : "Something went wrong"}
              </CardTitle>
              <CardDescription>
                {isAppLevel
                  ? "The application encountered an unexpected error"
                  : "This component failed to load properly"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground">
                  <strong>Error ID:</strong> {this.state.errorId}
                </p>
                {process.env.NODE_ENV === "development" && this.state.error && (
                  <details className="mt-2">
                    <summary className="text-sm font-medium cursor-pointer">Technical Details</summary>
                    <pre className="mt-2 text-xs bg-background p-2 rounded border overflow-auto max-h-32">
                      {this.state.error.message}
                      {this.state.error.stack && `\n\n${this.state.error.stack}`}
                    </pre>
                  </details>
                )}
              </div>

              <div className="flex gap-2">
                <Button onClick={this.handleRetry} className="flex-1 bg-transparent" variant="outline">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
                {isAppLevel && (
                  <Button onClick={this.handleGoHome} variant="default">
                    <Home className="w-4 h-4 mr-2" />
                    Home
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

// Convenience wrapper components
export const AppErrorBoundary = ({ children, ...props }: Omit<Props, "level">) => (
  <ErrorBoundary level="app" {...props}>
    {children}
  </ErrorBoundary>
)

export const PageErrorBoundary = ({ children, ...props }: Omit<Props, "level">) => (
  <ErrorBoundary level="page" {...props}>
    {children}
  </ErrorBoundary>
)

export const ComponentErrorBoundary = ({ children, ...props }: Omit<Props, "level">) => (
  <ErrorBoundary level="component" {...props}>
    {children}
  </ErrorBoundary>
)
