"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { AuthForm } from "@/components/auth-form"
import { RouteGuard } from "@/components/route-guard"

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login")
  const router = useRouter()

  const handleToggleMode = () => {
    setMode(mode === "login" ? "signup" : "login")
  }

  const handleSuccess = () => {
    // Navigate to chat page after successful authentication
    router.push("/chat")
  }

  return (
    <RouteGuard requireAuth={false} redirectTo="/chat">
      <AuthForm mode={mode} onToggleMode={handleToggleMode} onSuccess={handleSuccess} />
    </RouteGuard>
  )
}
