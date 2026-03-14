"use client"

import { motion } from "framer-motion"
import { Wifi, WifiOff, Loader2 } from "lucide-react"

type ApiStatusType = "healthy" | "checking" | "error" | "offline"

interface ConnectionStatusProps {
  status: ApiStatusType
  className?: string
}

export function ConnectionStatus({ status, className = "" }: ConnectionStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case "healthy":
        return {
          icon: Wifi,
          text: "Connected",
          color: "text-green-500",
          bgColor: "bg-green-500/10",
        }
      case "checking":
        return {
          icon: Loader2,
          text: "Checking...",
          color: "text-yellow-500",
          bgColor: "bg-yellow-500/10",
          animate: true,
        }
      case "error":
        return {
          icon: WifiOff,
          text: "Error",
          color: "text-orange-500",
          bgColor: "bg-orange-500/10",
        }
      case "offline":
        return {
          icon: WifiOff,
          text: "Disconnected",
          color: "text-red-500",
          bgColor: "bg-red-500/10",
        }
      default:
        return {
          icon: WifiOff,
          text: "Unknown",
          color: "text-gray-500",
          bgColor: "bg-gray-500/10",
        }
    }
  }

  const config = getStatusConfig()
  const Icon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.bgColor} ${className}`}
    >
      <Icon className={`w-4 h-4 ${config.color} ${config.animate ? "animate-spin" : ""}`} />
      <span className={`text-xs font-medium ${config.color}`}>{config.text}</span>
    </motion.div>
  )
}
