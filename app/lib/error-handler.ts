interface ErrorContext {
  component?: string
  action?: string
  userId?: string
  sessionId?: string
  timestamp: string
  userAgent?: string
  url?: string
}

interface ErrorReport {
  message: string
  stack?: string
  context: ErrorContext
  severity: "low" | "medium" | "high" | "critical"
  category: "api" | "ui" | "websocket" | "auth" | "validation" | "network" | "unknown"
}

class ErrorHandler {
  private static instance: ErrorHandler
  private errorQueue: ErrorReport[] = []
  private isOnline = true

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler()
    }
    return ErrorHandler.instance
  }

  constructor() {
    if (typeof window !== "undefined") {
      // Global error handlers
      window.addEventListener("error", this.handleGlobalError.bind(this))
      window.addEventListener("unhandledrejection", this.handleUnhandledRejection.bind(this))
      window.addEventListener("online", () => {
        this.isOnline = true
      })
      window.addEventListener("offline", () => {
        this.isOnline = false
      })
    }
  }

  private handleGlobalError(event: ErrorEvent) {
    this.logError(
      new Error(event.message),
      {
        component: "Global",
        action: "unhandled_error",
        timestamp: new Date().toISOString(),
        url: event.filename,
      },
      "high",
      "unknown",
    )
  }

  private handleUnhandledRejection(event: PromiseRejectionEvent) {
    const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason))
    this.logError(
      error,
      {
        component: "Global",
        action: "unhandled_promise_rejection",
        timestamp: new Date().toISOString(),
      },
      "high",
      "unknown",
    )
  }

  logError(
    error: Error,
    context: Partial<ErrorContext>,
    severity: ErrorReport["severity"] = "medium",
    category: ErrorReport["category"] = "unknown",
  ) {
    const errorReport: ErrorReport = {
      message: error.message,
      stack: error.stack,
      context: {
        timestamp: new Date().toISOString(),
        userAgent: typeof window !== "undefined" ? window.navigator.userAgent : undefined,
        url: typeof window !== "undefined" ? window.location.href : undefined,
        ...context,
      },
      severity,
      category,
    }

    // Log to console with appropriate level
    const logLevel = severity === "critical" || severity === "high" ? "error" : severity === "medium" ? "warn" : "log"
    
    // Safely call console method
    if (logLevel === "error") {
      console.error(`[ErrorHandler] ${category.toUpperCase()}:`, errorReport)
    } else if (logLevel === "warn") {
      console.warn(`[ErrorHandler] ${category.toUpperCase()}:`, errorReport)
    } else {
      console.log(`[ErrorHandler] ${category.toUpperCase()}:`, errorReport)
    }

    // Queue for potential reporting
    this.errorQueue.push(errorReport)

    // Keep queue size manageable
    if (this.errorQueue.length > 100) {
      this.errorQueue = this.errorQueue.slice(-50)
    }
  }

  getErrorStats() {
    const now = Date.now()
    const last24h = this.errorQueue.filter((e) => now - new Date(e.context.timestamp).getTime() < 24 * 60 * 60 * 1000)

    return {
      total: this.errorQueue.length,
      last24h: last24h.length,
      byCategory: this.errorQueue.reduce(
        (acc, error) => {
          acc[error.category] = (acc[error.category] || 0) + 1
          return acc
        },
        {} as Record<string, number>,
      ),
      bySeverity: this.errorQueue.reduce(
        (acc, error) => {
          acc[error.severity] = (acc[error.severity] || 0) + 1
          return acc
        },
        {} as Record<string, number>,
      ),
    }
  }

  clearErrors() {
    this.errorQueue = []
  }
}

export const errorHandler = ErrorHandler.getInstance()

// Helper functions for common error scenarios
export const handleApiError = (error: Error, context: Partial<ErrorContext>) => {
  errorHandler.logError(error, context, "medium", "api")
}

export const handleAuthError = (error: Error, context: Partial<ErrorContext>) => {
  errorHandler.logError(error, context, "high", "auth")
}

export const handleWebSocketError = (error: Error, context: Partial<ErrorContext>) => {
  errorHandler.logError(error, context, "medium", "websocket")
}

export const handleValidationError = (error: Error, context: Partial<ErrorContext>) => {
  errorHandler.logError(error, context, "low", "validation")
}

export const handleNetworkError = (error: Error, context: Partial<ErrorContext>) => {
  errorHandler.logError(error, context, "high", "network")
}
