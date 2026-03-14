"use client"

import { AppShell } from "@/components/app-shell"
import { RouteGuard } from "@/components/route-guard"

export default function ChatPage() {
  return (
    <RouteGuard requireAuth={true} redirectTo="/auth">
      <AppShell />
    </RouteGuard>
  )
}
