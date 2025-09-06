"use client"

import React, { useEffect, useRef, useCallback } from "react"

interface PerformanceMetrics {
  renderCount: number
  lastRenderTime: number
  averageRenderTime: number
  totalRenderTime: number
  apiCallCount: number
  cacheHits: number
  cacheMisses: number
}

interface PerformanceOptions {
  enableLogging?: boolean
  trackRenders?: boolean
  trackApiCalls?: boolean
  logInterval?: number
}

export function usePerformanceMonitor(
  componentName: string,
  options: PerformanceOptions = {}
) {
  const {
    enableLogging = process.env.NODE_ENV === 'development',
    trackRenders = true,
    trackApiCalls = true,
    logInterval = 5000
  } = options

  const metricsRef = useRef<PerformanceMetrics>({
    renderCount: 0,
    lastRenderTime: 0,
    averageRenderTime: 0,
    totalRenderTime: 0,
    apiCallCount: 0,
    cacheHits: 0,
    cacheMisses: 0
  })

  const renderStartTimeRef = useRef<number>(0)
  const lastLogTimeRef = useRef<number>(Date.now())

  // Track render performance
  useEffect(() => {
    if (!trackRenders) return

    const renderStartTime = renderStartTimeRef.current || performance.now()
    const renderEndTime = performance.now()
    const renderDuration = renderEndTime - renderStartTime

    metricsRef.current.renderCount++
    metricsRef.current.lastRenderTime = renderDuration
    metricsRef.current.totalRenderTime += renderDuration
    metricsRef.current.averageRenderTime = 
      metricsRef.current.totalRenderTime / metricsRef.current.renderCount

    renderStartTimeRef.current = 0

    // Log performance metrics periodically
    if (enableLogging && Date.now() - lastLogTimeRef.current > logInterval) {
      console.group(`🚀 Performance Metrics - ${componentName}`)
      console.log('Renders:', metricsRef.current.renderCount)
      console.log('Avg Render Time:', `${metricsRef.current.averageRenderTime.toFixed(2)}ms`)
      console.log('Last Render Time:', `${metricsRef.current.lastRenderTime.toFixed(2)}ms`)
      console.log('API Calls:', metricsRef.current.apiCallCount)
      console.log('Cache Hit Rate:', 
        metricsRef.current.cacheHits + metricsRef.current.cacheMisses > 0
          ? `${((metricsRef.current.cacheHits / (metricsRef.current.cacheHits + metricsRef.current.cacheMisses)) * 100).toFixed(1)}%`
          : 'N/A'
      )
      console.groupEnd()
      lastLogTimeRef.current = Date.now()
    }
  })

  // Mark render start
  const markRenderStart = useCallback(() => {
    if (trackRenders) {
      renderStartTimeRef.current = performance.now()
    }
  }, [trackRenders])

  // Track API calls
  const trackApiCall = useCallback(() => {
    if (trackApiCalls) {
      metricsRef.current.apiCallCount++
    }
  }, [trackApiCalls])

  // Track cache hits/misses
  const trackCacheHit = useCallback(() => {
    metricsRef.current.cacheHits++
  }, [])

  const trackCacheMiss = useCallback(() => {
    metricsRef.current.cacheMisses++
  }, [])

  // Get current metrics
  const getMetrics = useCallback(() => ({ ...metricsRef.current }), [])

  // Reset metrics
  const resetMetrics = useCallback(() => {
    metricsRef.current = {
      renderCount: 0,
      lastRenderTime: 0,
      averageRenderTime: 0,
      totalRenderTime: 0,
      apiCallCount: 0,
      cacheHits: 0,
      cacheMisses: 0
    }
  }, [])

  // Mark render start on every render
  markRenderStart()

  return {
    trackApiCall,
    trackCacheHit,
    trackCacheMiss,
    getMetrics,
    resetMetrics
  }
}

// HOC for automatic performance tracking
export function withPerformanceMonitor<P extends object>(
  Component: React.ComponentType<P>,
  componentName?: string
) {
  const WrappedComponent = (props: P) => {
    const name = componentName || Component.displayName || Component.name || 'Unknown'
    usePerformanceMonitor(name)
    return React.createElement(Component, props)
  }

  WrappedComponent.displayName = `withPerformanceMonitor(${componentName || Component.displayName || Component.name})`
  return WrappedComponent
}

// Performance utilities
export const performanceUtils = {
  // Debounce function for performance optimization
  debounce: <T extends (...args: any[]) => any>(
    func: T,
    wait: number
  ): ((...args: Parameters<T>) => void) => {
    let timeout: NodeJS.Timeout
    return (...args: Parameters<T>) => {
      clearTimeout(timeout)
      timeout = setTimeout(() => func(...args), wait)
    }
  },

  // Throttle function for performance optimization
  throttle: <T extends (...args: any[]) => any>(
    func: T,
    limit: number
  ): ((...args: Parameters<T>) => void) => {
    let inThrottle: boolean
    return (...args: Parameters<T>) => {
      if (!inThrottle) {
        func(...args)
        inThrottle = true
        setTimeout(() => inThrottle = false, limit)
      }
    }
  },

  // Batch state updates
  batchUpdates: (updates: (() => void)[]) => {
    // Use React's unstable_batchedUpdates if available
    if ('unstable_batchedUpdates' in React) {
      ;(React as any).unstable_batchedUpdates(() => {
        updates.forEach(update => update())
      })
    } else {
      // Fallback for newer React versions with automatic batching
      updates.forEach(update => update())
    }
  }
}
