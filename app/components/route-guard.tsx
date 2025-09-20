"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/use-auth"

interface RouteGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  redirectTo?: string
}

export function RouteGuard({ children, requireAuth = true, redirectTo }: RouteGuardProps) {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    if (!loading) {
      if (requireAuth && !isAuthenticated) {
        router.push(redirectTo || "/auth")
        return
      }

      if (!requireAuth && isAuthenticated) {
        // Navigate immediately when user is authenticated on auth page
        router.push(redirectTo || "/chat")
        return
      }

      setIsAuthorized(true)
    }
  }, [isAuthenticated, loading, requireAuth, redirectTo, router])

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-secondary/20">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground mb-2">Checking authentication...</p>
          <p className="text-xs text-muted-foreground/70">This may take a few moments</p>
        </div>
      </div>
    )
  }

  if (!isAuthorized) {
    return null
  }

  return <>{children}</>
}
