interface LogLevel {
  DEBUG: "debug"
  INFO: "info"
  WARN: "warn"
  ERROR: "error"
}

const LOG_LEVELS: LogLevel = {
  DEBUG: "debug",
  INFO: "info",
  WARN: "warn",
  ERROR: "error",
}

class Logger {
  private isDevelopment = process.env.NODE_ENV === "development"

  private log(level: keyof LogLevel, message: string, ...args: unknown[]) {
    if (!this.isDevelopment && level === "DEBUG") return

    const timestamp = new Date().toISOString()
    const prefix = `[${timestamp}] [WebSocket] [${level}]`

    switch (level) {
      case "ERROR":
        console.error(prefix, message, ...args)
        break
      case "WARN":
        console.warn(prefix, message, ...args)
        break
      case "INFO":
        console.info(prefix, message, ...args)
        break
      case "DEBUG":
      default:
        console.log(prefix, message, ...args)
        break
    }
  }

  debug(message: string, ...args: unknown[]) {
    this.log("DEBUG", message, ...args)
  }

  info(message: string, ...args: unknown[]) {
    this.log("INFO", message, ...args)
  }

  warn(message: string, ...args: unknown[]) {
    this.log("WARN", message, ...args)
  }

  error(message: string, ...args: unknown[]) {
    this.log("ERROR", message, ...args)
  }
}

const logger = new Logger()

export interface WebSocketMessage {
  type: "connected" | "typing" | "response_chunk" | "response_complete" | "pong" | "error"
  session_id?: string
  user_id?: string
  content?: string
  is_final?: boolean
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, unknown>
  error?: string
  error_code?: string
  timestamp: string
}

export interface ChatMessage {
  type: "chat" | "ping"
  content?: string
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected" | "reconnecting"

export interface WebSocketClientOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnectionChange?: (status: ConnectionStatus) => void
  onError?: (error: string) => void
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private wsUrl: string
  private accessToken: string | null = null
  private sessionId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000 // Start with 1 second
  private maxReconnectDelay = 30000 // Max 30 seconds
  private reconnectTimer: NodeJS.Timeout | null = null
  private pingInterval: NodeJS.Timeout | null = null
  private connectionStatus: ConnectionStatus = "disconnected"
  private options: WebSocketClientOptions

  constructor(wsUrl: string, options: WebSocketClientOptions = {}) {
    this.wsUrl = wsUrl
    this.options = options
  }

  connect(accessToken: string, sessionId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.accessToken = accessToken
      this.sessionId = sessionId || null
      this.setConnectionStatus("connecting")

      try {
        this.ws = new WebSocket(this.wsUrl)

        this.ws.onopen = () => {
          logger.info("WebSocket connected")
          this.reconnectAttempts = 0
          this.reconnectDelay = 1000

          // Send authentication message
          this.sendAuth()

          // Start ping interval
          this.startPingInterval()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            logger.debug("WebSocket message received:", message.type)

            if (message.type === "connected") {
              this.setConnectionStatus("connected")
              if (message.session_id && !this.sessionId) {
                this.sessionId = message.session_id
              }
              resolve()
            }

            this.options.onMessage?.(message)
          } catch (error) {
            logger.error("Failed to parse WebSocket message:", error)
            this.options.onError?.("Failed to parse message")
          }
        }

        this.ws.onclose = (event) => {
          logger.info("WebSocket closed:", event.code, event.reason)
          this.setConnectionStatus("disconnected")
          this.stopPingInterval()

          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          logger.error("WebSocket error:", error)
          this.options.onError?.("Connection error")
          reject(new Error("WebSocket connection failed"))
        }
      } catch (error) {
        logger.error("Failed to create WebSocket:", error)
        this.setConnectionStatus("disconnected")
        reject(error)
      }
    })
  }

  private sendAuth(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.accessToken) {
      const authMessage = {
        access_token: this.accessToken,
        ...(this.sessionId && { session_id: this.sessionId }),
      }
      this.ws.send(JSON.stringify(authMessage))
      logger.debug("Sent auth message")
    }
  }

  sendChat(content: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: ChatMessage = {
        type: "chat",
        content,
      }
      this.ws.send(JSON.stringify(message))
      logger.debug("Sent chat message")
    } else {
      logger.warn("Cannot send message: WebSocket not connected")
      this.options.onError?.("Not connected")
    }
  }

  ping(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: ChatMessage = { type: "ping" }
      this.ws.send(JSON.stringify(message))
    }
  }

  private startPingInterval(): void {
    this.stopPingInterval()
    this.pingInterval = setInterval(() => {
      this.ping()
    }, 30000) // Ping every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.setConnectionStatus("reconnecting")
    this.reconnectAttempts++

    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay)

    logger.info(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`)

    this.reconnectTimer = setTimeout(() => {
      if (this.accessToken) {
        this.connect(this.accessToken, this.sessionId).catch((error) => {
          logger.error("Reconnect failed:", error)
        })
      }
    }, delay)
  }

  private setConnectionStatus(status: ConnectionStatus): void {
    if (this.connectionStatus !== status) {
      this.connectionStatus = status
      logger.debug("Connection status changed:", status)
      this.options.onConnectionChange?.(status)
    }
  }

  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus
  }

  getSessionId(): string | null {
    return this.sessionId
  }

  disconnect(): void {
    logger.info("Disconnecting WebSocket")
    this.stopPingInterval()

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close(1000, "Client disconnect")
      this.ws = null
    }

    this.setConnectionStatus("disconnected")
    this.reconnectAttempts = 0
  }
}
