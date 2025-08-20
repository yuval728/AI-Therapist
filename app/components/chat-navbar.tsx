"use client"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { LogOut, User, Brain } from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { motion } from "framer-motion"

interface ChatNavbarProps {
  onLogout: () => void
}

export function ChatNavbar({ onLogout }: ChatNavbarProps) {
  const { user } = useAuth()

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="sticky top-0 z-10 bg-background/80 backdrop-blur-xl border-b border-border/50"
    >
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-3"
          >
            <motion.div
              whileHover={{ rotate: 360 }}
              transition={{ duration: 0.6 }}
              className="w-10 h-10 bg-gradient-to-br from-primary/10 to-primary/5 rounded-full flex items-center justify-center shadow-sm"
            >
              <Brain className="w-5 h-5 text-primary" />
            </motion.div>
            <div>
              <h1 className="font-manrope font-semibold text-foreground">AI Therapist</h1>
              <p className="text-xs text-muted-foreground">Your mental health companion</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex items-center gap-3"
          >
            <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
              <span>Welcome, {user?.email?.split("@")[0]}</span>
            </div>

            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}>
              <Avatar className="w-8 h-8 border border-border/50 shadow-sm">
                <AvatarFallback className="bg-gradient-to-br from-accent/10 to-accent/5 text-accent text-xs">
                  <User className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
            </motion.div>

            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={onLogout}
                className="text-muted-foreground hover:text-foreground transition-colors hover:bg-secondary/50"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline ml-2">Logout</span>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </motion.nav>
  )
}
