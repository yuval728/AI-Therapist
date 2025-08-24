"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { SessionList } from "@/components/session-list"
import { ChatArea } from "@/components/chat-area"
import { SessionSummary } from "@/components/session-summary"
import { UserPreferences } from "@/components/user-preferences"
import { HealthStatus } from "@/components/health-status"
import { ConnectionStatus } from "@/components/connection-status"
import { DemoBanner } from "@/components/demo-banner"
import { useAuth } from "@/hooks/use-auth"
import { useSessionManagement } from "@/hooks/use-session-management"
import { useWebSocketChat } from "@/hooks/use-websocket-chat"
import { apiClient } from "@/lib/api"
import { Brain, User, LogOut, Settings, BarChart3, FileText, Menu, X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { useRouter } from "next/navigation"
import { useToast } from "@/hooks/use-toast"

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [rightPanelTab, setRightPanelTab] = useState("summary")
  const { user, logout } = useAuth()
  const router = useRouter()
  const { toast } = useToast()

  const {
    sessions,
    activeSessionId,
    loading: sessionsLoading,
    hasMore,
    createSession,
    setActiveSession,
    getActiveSession,
    loadMoreSessions,
    initializeSessions,
    searchSessions,
  } = useSessionManagement()

  const {
    messages,
    connectionStatus,
    isTyping,
    streamingState,
    error: chatError,
    connect,
    sendMessage,
    disconnect,
    getSessionId,
  } = useWebSocketChat(activeSessionId || undefined)

  // Initialize sessions on mount
  useEffect(() => {
    initializeSessions()
  }, [initializeSessions])

  // Guard to prevent duplicate initial session creation under React Strict Mode
  const createdInitialSessionRef = useRef(false)

  // Connect WebSocket when active session changes
  useEffect(() => {
    if (activeSessionId) {
      connect()
    } else {
      disconnect()
    }

    return () => disconnect()
  }, [activeSessionId, connect, disconnect])

  // Create initial session if none exists
  useEffect(() => {
    if (!sessionsLoading && sessions.length === 0 && !activeSessionId && !createdInitialSessionRef.current) {
      createdInitialSessionRef.current = true
      handleNewSession()
    }
  }, [sessionsLoading, sessions.length, activeSessionId])

  const handleNewSession = async () => {
    try {
      await createSession()
      setSidebarOpen(false) // Close sidebar on mobile after creating session
    } catch (error) {
      console.error("Failed to create session:", error)
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    setActiveSession(sessionId)
    setSidebarOpen(false) // Close sidebar on mobile after selecting session
  }

  const handleLogout = () => {
    disconnect()
    logout()
    toast({
      title: "Logged out",
      description: "You have been successfully logged out.",
    })
    router.push("/auth")
  }

  const handleProfileClick = () => {
    router.push("/profile")
  }

  const handleStatsClick = () => {
    router.push("/stats")
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-background via-background to-secondary/20">
      {/* Demo Banner */}
      {apiClient.isDemoMode() && (
        <div className="px-4 pt-4">
          <DemoBanner />
        </div>
      )}

      {/* Header */}
      <motion.header
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="sticky top-0 z-20 bg-background/80 backdrop-blur-xl border-b border-border/50"
      >
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Left: Logo and Mobile Menu */}
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden text-muted-foreground hover:text-foreground"
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>

              <motion.div
                whileHover={{ rotate: 360 }}
                transition={{ duration: 0.6 }}
                className="w-10 h-10 bg-gradient-to-br from-primary/10 to-primary/5 rounded-full flex items-center justify-center shadow-sm"
              >
                <Brain className="w-5 h-5 text-primary" />
              </motion.div>

              <div>
                <h1 className="font-manrope font-semibold text-foreground">AI Therapist</h1>
                <p className="text-xs text-muted-foreground hidden sm:block">Your mental health companion</p>
              </div>
            </div>

            {/* Center: Connection Status */}
            <div className="hidden md:block">
              <ConnectionStatus status={connectionStatus} />
            </div>

            {/* Right: User Menu */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                <span>Welcome, {user?.email?.split("@")[0]}</span>
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}>
                    <Button variant="ghost" size="sm" className="relative h-8 w-8 rounded-full">
                      <Avatar className="h-8 w-8 border border-border/50 shadow-sm">
                        <AvatarFallback className="bg-gradient-to-br from-accent/10 to-accent/5 text-accent text-xs">
                          <User className="w-4 h-4" />
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </motion.div>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      <p className="font-medium">{user?.email?.split("@")[0]}</p>
                      <p className="w-[200px] truncate text-sm text-muted-foreground">{user?.email}</p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleProfileClick}>
                    <User className="mr-2 h-4 w-4" />
                    <span>Profile</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setRightPanelTab("preferences")}>
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Preferences</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleStatsClick}>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    <span>Stats</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Sign out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Mobile Connection Status */}
          <div className="md:hidden mt-2 flex justify-center">
            <ConnectionStatus status={connectionStatus} />
          </div>
        </div>
      </motion.header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <AnimatePresence>
          {(sidebarOpen || window.innerWidth >= 1024) && (
            <motion.aside
              initial={{ x: -320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
              className={cn(
                "w-80 flex-shrink-0 z-10",
                "lg:relative lg:z-auto",
                "fixed inset-y-0 left-0 lg:translate-x-0",
                sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
              )}
            >
              <SessionList
                sessions={sessions}
                activeSessionId={activeSessionId}
                loading={sessionsLoading}
                hasMore={hasMore}
                onSessionSelect={handleSessionSelect}
                onNewSession={handleNewSession}
                onLoadMore={loadMoreSessions}
                onSearch={searchSessions}
              />
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Overlay for mobile */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSidebarOpen(false)}
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-5 lg:hidden"
            />
          )}
        </AnimatePresence>

        {/* Main Chat Area */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col">
            <ChatArea
              messages={messages}
              isTyping={isTyping}
              streamingState={streamingState}
              onSendMessage={sendMessage}
              connectionStatus={connectionStatus}
              error={chatError}
              activeSession={getActiveSession()}
            />
          </div>

          {/* Right Panel */}
          <motion.aside
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="hidden xl:block w-80 flex-shrink-0 bg-background/30 backdrop-blur-sm border-l border-border/50"
          >
            <Tabs value={rightPanelTab} onValueChange={setRightPanelTab} className="h-full flex flex-col">
              <div className="p-4 border-b border-border/50">
                <TabsList className="grid w-full grid-cols-3 glass">
                  <TabsTrigger value="summary" className="text-xs">
                    <FileText className="w-4 h-4 mr-1" />
                    Summary
                  </TabsTrigger>
                  <TabsTrigger value="preferences" className="text-xs">
                    <Settings className="w-4 h-4 mr-1" />
                    Settings
                  </TabsTrigger>
                  <TabsTrigger value="health" className="text-xs">
                    <BarChart3 className="w-4 h-4 mr-1" />
                    Health
                  </TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-hidden">
                <TabsContent value="summary" className="h-full m-0">
                  <SessionSummary sessionId={activeSessionId} />
                </TabsContent>
                <TabsContent value="preferences" className="h-full m-0">
                  <UserPreferences />
                </TabsContent>
                <TabsContent value="health" className="h-full m-0">
                  <HealthStatus />
                </TabsContent>
              </div>
            </Tabs>
          </motion.aside>
        </div>
      </div>
    </div>
  )
}
