"use client"

import { RouteGuard } from "@/components/route-guard"

export default function HomePage() {
  return (
    <RouteGuard requireAuth={false} redirectTo="/chat">
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-secondary/20">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting...</p>
        </div>
      </div>
    </RouteGuard>
  )
}
