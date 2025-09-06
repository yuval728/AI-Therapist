import { mockUser, mockChatHistory, getRandomTherapistResponse, simulateDelay } from "./mock-data"
import { apiCache } from "./api-cache"
import { requestDeduplicator } from "./request-deduplication"
import { handleApiError, handleAuthError, handleNetworkError } from "./error-handler"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api"
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/chat"

const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true" || !process.env.NEXT_PUBLIC_API_BASE_URL

interface APIResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

interface AuthTokens {
  access_token: string
  refresh_token: string
  user: User
}

interface User {
  id: string
  email: string
  full_name?: string
  created_at?: string
}

interface TherapySession {
  id: string
  user_id: string
  emotion?: string
  crisis_level?: number
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
  ended_at?: string
}

interface SessionMessage {
  id: string
  session_id: string
  role: "user" | "assistant"
  content: string
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, unknown>
  created_at: string
}

interface BackendAuthResponse {
  user: {
    id: string
    email: string
    full_name?: string
    created_at?: string
  }
  tokens: {
    access_token: string
    refresh_token: string
    token_type: string
  }
  profile?: Record<string, unknown>
}

interface BackendMessageResponse {
  id: string
  session_id: string
  message_type: string
  content: string
  emotion_detected?: string
  emotion?: string
  crisis_level?: number
  mode?: string
  metadata?: Record<string, unknown>
  created_at: string
}

interface BackendUserProfileResponse {
  id: string
  email: string
  full_name?: string
  preferences?: Record<string, unknown>
  created_at: string
  updated_at: string
}

class ApiClient {
  private getAuthHeaders(): HeadersInit {
    const token = this.getAccessToken()
    return {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
    }
  }

  private getAccessToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("access_token")
    }
    return null
  }

  private getRefreshToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("refresh_token")
    }
    return null
  }

  private setTokens(tokens: AuthTokens): void {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", tokens.access_token)
      localStorage.setItem("refresh_token", tokens.refresh_token)
      localStorage.setItem("user", JSON.stringify(tokens.user))

      // Set HTTP-only cookie for middleware
      const maxAge = 7 * 24 * 60 * 60 // 7 days
      document.cookie = `access_token=${tokens.access_token}; path=/; max-age=${maxAge}; samesite=strict`
    }
  }

  private removeTokens(): void {
    if (typeof window !== "undefined") {
      const keysToRemove = ["access_token", "refresh_token", "user"]
      keysToRemove.forEach((key) => localStorage.removeItem(key))

      document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"

      // Notify listeners (e.g., useAuth) that auth tokens were cleared
      try {
        window.dispatchEvent(new Event("auth:logout"))
      } catch {
        // no-op: event dispatch might fail in non-browser envs
      }
    }
  }

  private retryQueue = new Map<string, { retries: number; lastAttempt: number }>()
  private maxRetries = 3
  private retryDelay = 1000

  async signup(email: string, password: string, fullName?: string): Promise<{ success: true; message?: string }> {
    if (isDemoMode) {
      await simulateDelay(800)
      // In demo mode, mimic sign-up success without creating a session
      return { success: true, message: "Registration successful (demo). Please sign in." }
    }

    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Backend SignUpRequest requires: email, password, confirm_password, full_name?, terms_accepted
      body: JSON.stringify({
        email,
        password,
        confirm_password: password,
        full_name: fullName,
        terms_accepted: true,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || "Signup failed")
    }

    const apiResponse: APIResponse<unknown> = await response.json()
    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Signup failed")
    }

    // Signup does not authenticate the user; return success and let UI switch to login
    return { success: true, message: apiResponse.message }
  }

  async signin(email: string, password: string): Promise<AuthTokens> {
    if (isDemoMode) {
      await simulateDelay(800)
      const mockTokens = {
        access_token: "demo-access-token-123",
        refresh_token: "demo-refresh-token-123",
        user: mockUser,
      }
      this.setTokens(mockTokens)
      return mockTokens
    }

    try {
      const response = await this.makeRequest(`${API_BASE_URL}/auth/signin`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })

      const apiResponse: APIResponse<BackendAuthResponse> = await response.json()
      if (!apiResponse.success || !apiResponse.data) {
        throw new Error(apiResponse.message || "Sign in failed")
      }

      const { user, tokens } = apiResponse.data
      if (!tokens?.access_token || !tokens?.refresh_token || !user) {
        throw new Error("Invalid signin response")
      }

      const flattened: AuthTokens = this.createAuthTokens(tokens, user)
      this.setTokens(flattened)
      return flattened
    } catch (error) {
      if (error instanceof Error) {
        if (error.message.includes("network") || error.message.includes("fetch")) {
          handleNetworkError(error, { component: "ApiClient", action: "signin", userId: email })
        } else {
          handleAuthError(error, { component: "ApiClient", action: "signin", userId: email })
        }
      }
      throw error
    }
  }

  async refreshToken(): Promise<AuthTokens> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      throw new Error("No refresh token available")
    }

    if (isDemoMode) {
      await simulateDelay(300)
      const mockTokens = {
        access_token: "demo-access-token-refreshed-123",
        refresh_token: refreshToken,
        user: mockUser,
      }
      this.setTokens(mockTokens)
      return mockTokens
    }

    try {
      const response = await this.makeRequest(
        `${API_BASE_URL}/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
        { method: "POST" },
      )

      const apiResponse: APIResponse<BackendAuthResponse> = await response.json()
      if (!apiResponse.success || !apiResponse.data) {
        throw new Error("Token refresh failed")
      }

      const { user, tokens } = apiResponse.data
      if (!tokens?.access_token || !tokens?.refresh_token || !user) {
        throw new Error("Invalid refresh response")
      }

      const flattened = this.createAuthTokens(tokens, user)
      this.setTokens(flattened)
      return flattened
    } catch (error) {
      this.removeTokens()
      if (error instanceof Error) {
        handleAuthError(error, { component: "ApiClient", action: "token_refresh", url: `${API_BASE_URL}/auth/refresh` })
      }
      throw error
    }
  }

  async getCurrentUser(): Promise<User> {
    const cacheKey = "current-user"
    const cached = apiCache.get<User>(cacheKey)
    if (cached) {
      return cached
    }

    return requestDeduplicator.deduplicate(cacheKey, async () => {
      return this.retryRequest(`getCurrentUser-${Date.now()}`, async () => {
        if (isDemoMode) {
          await simulateDelay(300)
          const user = mockUser
          apiCache.set(cacheKey, user, 10 * 60 * 1000)
          return user
        }

        try {
          const response = await this.fetchWithAuth(`${API_BASE_URL}/auth/me`)
          const apiResponse: APIResponse<{ user: User }> = await response.json()

          if (!apiResponse.success || !apiResponse.data) {
            throw new Error(apiResponse.message || "Failed to get user info")
          }

          const user = apiResponse.data.user
          apiCache.set(cacheKey, user, 10 * 60 * 1000)
          return user
        } catch (error) {
          if (error instanceof Error) {
            if (error.message === "Session expired") {
              handleAuthError(error, { component: "ApiClient", action: "getCurrentUser" })
            } else {
              handleApiError(error, { component: "ApiClient", action: "getCurrentUser" })
            }
          }
          throw error
        }
      })
    })
  }

  async signout(): Promise<void> {
    if (isDemoMode) {
      await simulateDelay(300)
      this.removeTokens()
      return
    }

    try {
      await this.fetchWithAuth(`${API_BASE_URL}/auth/signout`, { method: "POST" })
    } catch (error) {
      console.warn("Signout request failed:", error)
    } finally {
      this.removeTokens()
    }
  }

  async createSession(
    emotion?: string,
    crisis_level?: number,
    metadata?: Record<string, unknown>,
  ): Promise<TherapySession> {
    const result = await (async () => {
      if (isDemoMode) {
        await simulateDelay(500)
        return {
          id: `demo-session-${Date.now()}`,
          user_id: mockUser.id,
          emotion,
          crisis_level,
          metadata,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
      }

      const response = await this.fetchWithAuth(`${API_BASE_URL}/sessions/`, {
        method: "POST",
        body: JSON.stringify({ emotion, crisis_level, metadata }),
      })

      const apiResponse: APIResponse<TherapySession> = await response.json()
      if (!apiResponse.success || !apiResponse.data) {
        throw new Error(apiResponse.message || "Failed to create session")
      }

      return apiResponse.data
    })()

    // Invalidate sessions cache since we created a new session
    this.invalidateSessionsCache()
    return result
  }

  async getSessions(offset = 0, limit = 50): Promise<TherapySession[]> {
    const cacheKey = `sessions-${offset}-${limit}`
    const cached = apiCache.get<TherapySession[]>(cacheKey)
    if (cached) {
      return cached
    }

    return requestDeduplicator.deduplicate(cacheKey, async () => {
      return this.retryRequest(`getSessions-${offset}-${limit}`, async () => {
        if (isDemoMode) {
          await simulateDelay(400)
          const sessions = [
            {
              id: "demo-session-1",
              user_id: mockUser.id,
              emotion: "anxious",
              crisis_level: 2,
              created_at: new Date(Date.now() - 86400000).toISOString(),
              updated_at: new Date(Date.now() - 86400000).toISOString(),
            },
          ]
          apiCache.set(cacheKey, sessions, 2 * 60 * 1000)
          return sessions
        }

        const response = await this.fetchWithAuth(`${API_BASE_URL}/sessions/?offset=${offset}&limit=${limit}`)
        const apiResponse: APIResponse<TherapySession[]> = await response.json()

        if (!apiResponse.success || !apiResponse.data) {
          throw new Error(apiResponse.message || "Failed to get sessions")
        }

        const sessions = apiResponse.data
        apiCache.set(cacheKey, sessions, 2 * 60 * 1000)
        return sessions
      })
    })
  }

  async getSessionMessages(sessionId: string, offset = 0, limit = 50): Promise<SessionMessage[]> {
    const cacheKey = `session-messages-${sessionId}-${offset}-${limit}`
    const cached = apiCache.get<SessionMessage[]>(cacheKey)
    if (cached) {
      return cached
    }

    return requestDeduplicator.deduplicate(cacheKey, async () => {
      if (isDemoMode) {
        await simulateDelay(500)
        const messages = mockChatHistory.map((msg, index) => ({
          id: `demo-msg-${index}`,
          session_id: sessionId,
          role: msg.sender === "user" ? "user" : "assistant",
          content: msg.message,
          created_at: msg.timestamp,
        }))
        apiCache.set(cacheKey, messages, 1 * 60 * 1000)
        return messages
      }

      const response = await this.fetchWithAuth(
        `${API_BASE_URL}/sessions/${sessionId}/messages?offset=${offset}&limit=${limit}`,
      )
      const apiResponse: APIResponse<BackendMessageResponse[]> = await response.json()

      if (!apiResponse.success || !apiResponse.data) {
        throw new Error(apiResponse.message || "Failed to get session messages")
      }

      const mapped: SessionMessage[] = apiResponse.data.map((m: BackendMessageResponse) => ({
        id: m.id,
        session_id: m.session_id,
        role: m.message_type === "ai_response" || m.message_type === "system_message" ? "assistant" : "user",
        content: m.content,
        emotion: m.emotion_detected ?? m.emotion,
        crisis_level: m.crisis_level,
        mode: m.mode,
        metadata: m.metadata,
        created_at: m.created_at,
      }))

      apiCache.set(cacheKey, mapped, 1 * 60 * 1000)
      return mapped
    })
  }

  // New: fetch messages with pagination metadata
  async getSessionMessagesPaged(
    sessionId: string,
    offset = 0,
    limit = 50,
  ): Promise<{ messages: SessionMessage[]; total: number; has_more: boolean; offset: number; limit: number }> {
    if (isDemoMode) {
      const demo = await this.getSessionMessages(sessionId, offset, limit)
      return { messages: demo, total: demo.length, has_more: false, offset, limit }
    }

    const response = await this.fetchWithAuth(
      `${API_BASE_URL}/sessions/${sessionId}/messages?offset=${offset}&limit=${limit}`,
    )
    const apiResponse: APIResponse<BackendMessageResponse[]> & {
      metadata?: { total?: number; has_more?: boolean; offset?: number; limit?: number }
    } = await response.json()

    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to get session messages")
    }

    const meta = apiResponse.metadata || {}
    const mapped: SessionMessage[] = apiResponse.data.map((m: BackendMessageResponse) => ({
      id: m.id,
      session_id: m.session_id,
      role: m.message_type === "ai_response" || m.message_type === "system_message" ? "assistant" : "user",
      content: m.content,
      emotion: m.emotion_detected ?? m.emotion,
      crisis_level: m.crisis_level,
      mode: m.mode,
      metadata: m.metadata,
      created_at: m.created_at,
    }))

    return {
      messages: mapped,
      total: typeof meta.total === "number" ? meta.total : mapped.length,
      has_more: Boolean(meta.has_more),
      offset: typeof meta.offset === "number" ? meta.offset : offset,
      limit: typeof meta.limit === "number" ? meta.limit : limit,
    }
  }

  async getHealthStatus(): Promise<{ status: string; timestamp: string; service: string }> {
    const cacheKey = "health-status"
    const cached = apiCache.get<{ status: string; timestamp: string; service: string }>(cacheKey)
    if (cached) {
      return cached
    }

    return requestDeduplicator.deduplicate(cacheKey, async () => {
      if (isDemoMode) {
        await simulateDelay(200)
        const health = {
          status: "healthy",
          timestamp: new Date().toISOString(),
          service: "ai-therapist-demo",
        }
        apiCache.set(cacheKey, health, 30 * 60 * 1000)
        return health
      }

      const response = await fetch(`${API_BASE_URL}/health/`)
      const apiResponse: APIResponse<{ status: string; timestamp: string; service: string }> = await response.json()

      if (!apiResponse.success || !apiResponse.data) {
        throw new Error("Health check failed")
      }

      const health = apiResponse.data
      apiCache.set(cacheKey, health, 30 * 60 * 1000)
      return health
    })
  }

  async getUserProfile(): Promise<User> {
    if (isDemoMode) {
      await simulateDelay(300)
      return {
        ...mockUser,
        full_name: "Demo User",
        created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      }
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/users/profile`)
    const apiResponse: APIResponse<BackendUserProfileResponse> = await response.json()

    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to get user profile")
    }

    // Backend returns { id, email, full_name, preferences, created_at, updated_at }
    const data = apiResponse.data
    const mapped: User = {
      id: data.id,
      email: data.email,
      full_name: data.full_name,
      created_at: data.created_at,
    }
    return mapped
  }

  async updateUserProfile(updates: Partial<User> & { preferences?: Record<string, unknown> }): Promise<User> {
    if (isDemoMode) {
      await simulateDelay(500)
      return { ...mockUser, ...updates }
    }

    // Only send allowed fields to backend: full_name, preferences
    const payload: Record<string, unknown> = {}
    if (typeof updates.full_name === "string" && updates.full_name.trim().length > 0) {
      payload.full_name = updates.full_name
    }
    if (updates.preferences && typeof updates.preferences === "object") {
      payload.preferences = updates.preferences
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/users/profile`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })

    const apiResponse: APIResponse<BackendUserProfileResponse> = await response.json()
    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to update profile")
    }

    const data = apiResponse.data
    const mapped: User = {
      id: data.id,
      email: data.email,
      full_name: data.full_name,
      created_at: data.created_at,
    }
    return mapped
  }

  async getUserPreferences(): Promise<Record<string, unknown>> {
    if (isDemoMode) {
      await simulateDelay(300)
      return {
        theme: "light",
        notifications: true,
        crisis_alerts: true,
        session_reminders: false,
        privacy_mode: false,
        language: "en",
      }
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/users/preferences`)
    const apiResponse: APIResponse<Record<string, unknown>> = await response.json()

    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to get preferences")
    }

    return apiResponse.data
  }

  async updateUserPreferences(preferences: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (isDemoMode) {
      await simulateDelay(500)
      return preferences
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/users/preferences`, {
      method: "PUT",
      body: JSON.stringify(preferences),
    })

    const apiResponse: APIResponse<Record<string, unknown>> = await response.json()
    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to update preferences")
    }

    return apiResponse.data
  }

  async getUserStats(): Promise<Record<string, unknown>> {
    const cacheKey = "user-stats"
    const cached = apiCache.get<Record<string, unknown>>(cacheKey)
    if (cached) {
      return cached
    }

    return requestDeduplicator.deduplicate(cacheKey, async () => {
      if (isDemoMode) {
        await simulateDelay(400)
        const stats = {
          total_sessions: 12,
          total_messages: 156,
          avg_session_duration: 25.5,
          most_common_emotion: "anxious",
          improvement_score: 7.2,
          streak_days: 5,
          last_session: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          weekly_sessions: [2, 3, 1, 4, 2, 1, 0],
          emotion_distribution: {
            anxious: 35,
            sad: 20,
            happy: 15,
            stressed: 20,
            confused: 10,
          },
        }
        apiCache.set(cacheKey, stats, 5 * 60 * 1000)
        return stats
      }

      const response = await this.fetchWithAuth(`${API_BASE_URL}/users/stats`)
      const apiResponse: APIResponse<Record<string, unknown>> = await response.json()

      if (!apiResponse.success || !apiResponse.data) {
        throw new Error(apiResponse.message || "Failed to get user stats")
      }

      const stats = apiResponse.data
      apiCache.set(cacheKey, stats, 5 * 60 * 1000)
      return stats
    })
  }

  async getSessionSummary(sessionId: string): Promise<Record<string, unknown>> {
    if (isDemoMode) {
      await simulateDelay(600)
      return {
        session_id: sessionId,
        duration_minutes: 23,
        message_count: 14,
        primary_emotions: ["anxious", "hopeful"],
        key_topics: ["work stress", "coping strategies", "self-care"],
        insights: [
          "User expressed feeling overwhelmed with work responsibilities",
          "Showed openness to trying new coping mechanisms",
          "Demonstrated good self-awareness about stress triggers",
        ],
        recommendations: [
          "Continue practicing deep breathing exercises",
          "Consider setting boundaries at work",
          "Schedule regular self-care activities",
        ],
        crisis_level: 2,
        improvement_indicators: ["increased self-awareness", "willingness to try new strategies"],
      }
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/summary`)
    const apiResponse: APIResponse<Record<string, unknown>> = await response.json()

    if (!apiResponse.success || !apiResponse.data) {
      throw new Error(apiResponse.message || "Failed to get session summary")
    }

    return apiResponse.data
  }

  async deleteUserAccount(): Promise<void> {
    if (isDemoMode) {
      await simulateDelay(800)
      this.removeTokens()
      return
    }

    const response = await this.fetchWithAuth(`${API_BASE_URL}/users/account`, {
      method: "DELETE",
    })

    if (!response.ok) {
      throw new Error("Failed to delete account")
    }

    this.removeTokens()
  }

  invalidateUserCache(): void {
    apiCache.invalidatePattern("current-user")
    apiCache.invalidatePattern("user-.*")
  }

  invalidateSessionsCache(): void {
    apiCache.invalidatePattern("sessions-.*")
  }

  invalidateSessionMessagesCache(sessionId?: string): void {
    if (sessionId) {
      apiCache.invalidatePattern(`session-messages-${sessionId}-.*`)
    } else {
      apiCache.invalidatePattern("session-messages-.*")
    }
  }

  invalidateAllUserData(): void {
    apiCache.invalidatePattern("current-user")
    apiCache.invalidatePattern("user-.*")
    apiCache.invalidatePattern("sessions-.*")
    apiCache.invalidatePattern("session-messages-.*")
    apiCache.invalidatePattern("health-status")
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = this.getAuthHeaders()

    try {
      let response = await fetch(url, {
        ...options,
        headers: { ...headers, ...options.headers },
      })

      // Handle 401 with token refresh
      if (response.status === 401 && this.getRefreshToken()) {
        try {
          await this.refreshToken()
          const newHeaders = this.getAuthHeaders()
          response = await fetch(url, {
            ...options,
            headers: { ...newHeaders, ...options.headers },
          })
        } catch (error) {
          this.removeTokens()
          if (error instanceof Error) {
            handleAuthError(error, { component: "ApiClient", action: "token_refresh", url })
          }
          throw new Error("Session expired")
        }
      }

      if (!response.ok) {
        if (response.status === 401) {
          this.removeTokens()
          const authError = new Error("Session expired")
          handleAuthError(authError, { component: "ApiClient", action: "auth_check", url })
          throw authError
        }

        const error = new Error(`Request failed: ${response.statusText}`)
        if (response.status >= 500) {
          handleApiError(error, { component: "ApiClient", action: "server_error", url })
        } else if (response.status >= 400) {
          handleApiError(error, { component: "ApiClient", action: "client_error", url })
        }
        throw error
      }

      return response
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        handleNetworkError(error, { component: "ApiClient", action: "network_request", url })
      }
      throw error
    }
  }

  private createAuthTokens(
    tokens: { access_token: string; refresh_token: string; token_type: string },
    user: { id: string; email: string },
  ): AuthTokens {
    return {
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      user: {
        id: user.id,
        email: user.email,
      },
    }
  }

  private async makeRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(error.message || `Request failed: ${response.statusText}`)
    }

    return response
  }

  async login(email: string, password: string): Promise<AuthTokens> {
    return this.signin(email, password)
  }

  async getChatHistory(): Promise<{ sender: "user" | "therapist"; message: string; timestamp: string }[]> {
    // This will be replaced by session-based message loading
    if (isDemoMode) {
      await simulateDelay(500)
      return [...mockChatHistory]
    }
    return []
  }

  async sendMessage(message: string): Promise<{ reply: string }> {
    // This will be replaced by WebSocket communication
    if (isDemoMode) {
      await simulateDelay(1200 + Math.random() * 800)
      return { reply: getRandomTherapistResponse() }
    }
    throw new Error("Use WebSocket for real-time messaging")
  }

  logout(): void {
    this.signout()
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken()
  }

  isDemoMode(): boolean {
    return isDemoMode
  }

  getWebSocketUrl(): string {
    return WS_URL
  }

  private async retryRequest<T>(key: string, requestFn: () => Promise<T>, maxRetries = this.maxRetries): Promise<T> {
    const queueItem = this.retryQueue.get(key) || { retries: 0, lastAttempt: 0 }

    try {
      const result = await requestFn()
      this.retryQueue.delete(key)
      return result
    } catch (error) {
      if (queueItem.retries >= maxRetries) {
        this.retryQueue.delete(key)
        throw error
      }

      const delay = this.retryDelay * Math.pow(2, queueItem.retries)
      queueItem.retries++
      queueItem.lastAttempt = Date.now()
      this.retryQueue.set(key, queueItem)

      await new Promise((resolve) => setTimeout(resolve, delay))
      return this.retryRequest(key, requestFn, maxRetries)
    }
  }
}

export const apiClient = new ApiClient()
export type { User, TherapySession, SessionMessage, APIResponse }
