"use client"

import { Info } from "lucide-react"
import { motion } from "framer-motion"

export function DemoBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-950/20 dark:to-cyan-950/20 border border-blue-200 dark:border-blue-800/30 rounded-lg p-4 mb-4"
    >
      <div className="flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-1">Demo Mode Active</h3>
          <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
            You're currently using the demo version with simulated responses. All conversations are local and not saved.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-xs rounded-full">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
              No API required
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 text-xs rounded-full">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              Privacy-first
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
