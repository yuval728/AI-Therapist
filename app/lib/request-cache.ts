/**
 * Enhanced request cache and deduplication utility
 * Prevents duplicate API calls, caches responses, and optimizes performance
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  promise?: Promise<T>
  hits: number
  priority: 'high' | 'medium' | 'low'
}

interface RequestOptions {
  ttl?: number // Time to live in milliseconds
  dedupe?: boolean // Whether to deduplicate concurrent requests
  priority?: 'high' | 'medium' | 'low'
  skipCache?: boolean // Force fresh request
  background?: boolean // Low priority background request
}

interface CacheStats {
  hits: number
  misses: number
  size: number
  oldestEntry: number
}

class RequestCache {
  private cache = new Map<string, CacheEntry<any>>()
  private pendingRequests = new Map<string, Promise<any>>()
  private maxCacheSize = 500 // Prevent memory leaks
  private stats = { hits: 0, misses: 0 }
  
  private getCacheKey(url: string, options: RequestInit = {}): string {
    const sortedHeaders = Object.entries(options.headers || {})
      .sort(([a], [b]) => a.localeCompare(b))
    // Exclude common changing headers from cache key
    const stableHeaders = sortedHeaders.filter(([key]) => 
      !['user-agent', 'accept-encoding', 'connection'].includes(key.toLowerCase())
    )
    return `${options.method || 'GET'}:${url}:${JSON.stringify(stableHeaders)}:${options.body || ''}`
  }

  async fetch<T>(
    url: string, 
    fetchOptions: RequestInit = {}, 
    cacheOptions: RequestOptions = {}
  ): Promise<T> {
    const { 
      ttl = this.getTTLByEndpoint(url), 
      dedupe = true, 
      priority = 'medium',
      skipCache = false,
      background = false
    } = cacheOptions
    
    const cacheKey = this.getCacheKey(url, fetchOptions)
    
    // Check cache first (unless skipping)
    if (!skipCache) {
      const cached = this.cache.get(cacheKey)
      if (cached && Date.now() - cached.timestamp < ttl) {
        cached.hits++
        this.stats.hits++
        return cached.data
      }
    }
    
    this.stats.misses++

    // Check for pending request (deduplication)
    if (dedupe) {
      const pending = this.pendingRequests.get(cacheKey)
      if (pending) {
        return pending
      }
    }

    // Make new request with priority handling
    const requestPromise = background 
      ? this.makeBackgroundRequest<T>(url, fetchOptions)
      : this.makeRequest<T>(url, fetchOptions)
    
    if (dedupe) {
      this.pendingRequests.set(cacheKey, requestPromise)
    }

    try {
      const data = await requestPromise
      
      // Cache the result with priority and hit tracking
      this.cache.set(cacheKey, {
        data,
        timestamp: Date.now(),
        hits: 1,
        priority
      })
      
      // Maintain cache size
      this.evictOldEntries()
      
      return data
    } finally {
      // Clean up pending request
      this.pendingRequests.delete(cacheKey)
    }
  }

  private getTTLByEndpoint(url: string): number {
    // Smart TTL based on endpoint type
    if (url.includes('/sessions/')) {
      if (url.includes('/messages')) return 60000 // 1 minute for messages
      return 120000 // 2 minutes for sessions
    }
    if (url.includes('/auth/me')) return 300000 // 5 minutes for user info
    if (url.includes('/health')) return 10000 // 10 seconds for health
    return 30000 // 30 seconds default
  }

  private async makeRequest<T>(url: string, options: RequestInit): Promise<T> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 15000) // 15s timeout
    
    try {
      const response = await fetch(url, { 
        ...options, 
        signal: controller.signal,
        keepalive: true
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      return response.json()
    } finally {
      clearTimeout(timeoutId)
    }
  }

  private async makeBackgroundRequest<T>(url: string, options: RequestInit): Promise<T> {
    // Use scheduler API if available for background tasks
    if ('scheduler' in window && 'postTask' in (window as any).scheduler) {
      return (window as any).scheduler.postTask(() => this.makeRequest<T>(url, options), {
        priority: 'background'
      })
    }
    
    // Fallback to setTimeout for background priority
    return new Promise((resolve, reject) => {
      setTimeout(async () => {
        try {
          const result = await this.makeRequest<T>(url, options)
          resolve(result)
        } catch (error) {
          reject(error)
        }
      }, 0)
    })
  }

  private evictOldEntries(): void {
    if (this.cache.size <= this.maxCacheSize) return
    
    // Sort by priority and usage, remove oldest low-priority entries
    const entries = Array.from(this.cache.entries())
      .sort(([, a], [, b]) => {
        const priorityWeight = { high: 3, medium: 2, low: 1 }
        const aScore = priorityWeight[a.priority] * a.hits
        const bScore = priorityWeight[b.priority] * b.hits
        return aScore - bScore // Remove lowest scoring entries
      })
    
    const toRemove = entries.slice(0, this.cache.size - this.maxCacheSize + 50)
    toRemove.forEach(([key]) => this.cache.delete(key))
  }

  invalidate(pattern?: string): void {
    if (!pattern) {
      this.cache.clear()
      this.pendingRequests.clear()
      return
    }

    // Invalidate matching entries
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key)
      }
    }
    
    for (const key of this.pendingRequests.keys()) {
      if (key.includes(pattern)) {
        this.pendingRequests.delete(key)
      }
    }
  }

  // Prefetch data for anticipated requests
  async prefetch<T>(
    url: string, 
    fetchOptions: RequestInit = {}, 
    cacheOptions: RequestOptions = {}
  ): Promise<void> {
    try {
      await this.fetch<T>(url, fetchOptions, { 
        ...cacheOptions, 
        background: true, 
        priority: 'low' 
      })
    } catch (error) {
      // Silently fail prefetch requests
      console.debug('Prefetch failed:', url, error)
    }
  }

  getStats(): CacheStats {
    const now = Date.now()
    const entries = Array.from(this.cache.values())
    return {
      hits: this.stats.hits,
      misses: this.stats.misses,
      size: this.cache.size,
      oldestEntry: entries.length > 0 ? Math.min(...entries.map(e => now - e.timestamp)) : 0
    }
  }

  warmCache(urls: Array<{ url: string; options?: RequestInit }>): void {
    // Warm cache with commonly accessed endpoints
    urls.forEach(({ url, options }) => {
      this.prefetch(url, options, { priority: 'low', background: true })
    })
  }

  // Clean up expired entries
  cleanup(): void {
    const now = Date.now()
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > 300000) { // 5 minutes
        this.cache.delete(key)
      }
    }
  }
}

// Global cache instance
export const requestCache = new RequestCache()

// Auto cleanup every 5 minutes
if (typeof window !== 'undefined') {
  setInterval(() => requestCache.cleanup(), 300000)
}
