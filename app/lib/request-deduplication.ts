interface PendingRequest<T> {
  promise: Promise<T>
  timestamp: number
}

class RequestDeduplicator {
  private pendingRequests = new Map<string, PendingRequest<any>>()
  private readonly timeout = 30000 // 30 seconds

  async deduplicate<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    // Check if there's already a pending request for this key
    const existing = this.pendingRequests.get(key)
    if (existing) {
      // Check if the request hasn't timed out
      if (Date.now() - existing.timestamp < this.timeout) {
        return existing.promise
      } else {
        // Remove expired request
        this.pendingRequests.delete(key)
      }
    }

    // Create new request
    const promise = requestFn()
    this.pendingRequests.set(key, {
      promise,
      timestamp: Date.now(),
    })

    // Clean up after request completes
    promise
      .finally(() => {
        this.pendingRequests.delete(key)
      })
      .catch(() => {
        // Error handling is done by the caller
      })

    return promise
  }

  clear(): void {
    this.pendingRequests.clear()
  }
}

export const requestDeduplicator = new RequestDeduplicator()
