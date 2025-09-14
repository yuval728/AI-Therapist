"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { Settings, Save, Loader2, Palette } from "lucide-react"
import { motion } from "framer-motion"

interface Preferences {
  theme: "light" | "dark" | "system"
  language: "en" | "es" | "fr" | "de"
}

export function UserPreferences() {
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)
  const { toast } = useToast()
  const { theme, setTheme } = useTheme()

  const loadPreferences = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      setError(null)
      console.log("Loading preferences...")
      const prefs = await apiClient.getUserPreferences()
      if (mountedRef.current) {
        const prefsData = prefs as unknown as Preferences
        setPreferences(prefsData)
        console.log("Preferences loaded:", prefsData)
      }
    } catch (error) {
      if (mountedRef.current) {
        const errorMessage = error instanceof Error ? error.message : "Failed to load preferences"
        setError(errorMessage)
        console.error("Failed to load preferences:", error)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, []) // Remove theme and setTheme from dependencies to prevent infinite loop

  const savePreferences = useCallback(async () => {
    if (!preferences || !mountedRef.current) return

    try {
      setSaving(true)
      setError(null)
      await apiClient.updateUserPreferences(preferences as unknown as Record<string, unknown>)
      if (mountedRef.current) {
        toast({
          title: "Preferences saved",
          description: "Your preferences have been updated successfully.",
        })
      }
    } catch (error) {
      if (mountedRef.current) {
        const errorMessage = error instanceof Error ? error.message : "Failed to save preferences"
        setError(errorMessage)
        toast({
          title: "Save failed",
          description: errorMessage,
          variant: "destructive",
        })
      }
    } finally {
      if (mountedRef.current) {
        setSaving(false)
      }
    }
  }, [preferences, toast])

  const updatePreference = useCallback(
    <K extends keyof Preferences>(key: K, value: Preferences[K]) => {
      if (!preferences) return
      setPreferences({ ...preferences, [key]: value })
      
      // Immediately apply theme changes to next-themes
      if (key === "theme" && typeof value === "string") {
        setTheme(value)
      }
    },
    [preferences, setTheme],
  )

  useEffect(() => {
    mountedRef.current = true
    loadPreferences()

    return () => {
      mountedRef.current = false
    }
  }, [loadPreferences])

  // Separate effect to sync theme with preferences
  useEffect(() => {
    if (preferences?.theme && theme !== preferences.theme) {
      console.log(`Syncing theme from ${theme} to ${preferences.theme}`)
      setTheme(preferences.theme)
    }
  }, [preferences?.theme, theme, setTheme])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-primary" />
          <p className="text-sm text-muted-foreground">Loading preferences...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive" className="glass border-destructive/30">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  if (!preferences) return null

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-5 h-5 text-primary" />
            <h3 className="font-manrope font-semibold text-foreground">Preferences</h3>
          </div>
        </motion.div>

        {/* Appearance */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Palette className="w-4 h-4 text-primary" />
                Appearance
              </CardTitle>
              <CardDescription className="text-xs">Customize your visual experience</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="theme" className="text-sm">
                  Theme
                </Label>
                <Select
                  value={preferences.theme}
                  onValueChange={(value: Preferences["theme"]) => updatePreference("theme", value)}
                >
                  <SelectTrigger className="glass border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="language" className="text-sm">
                  Language
                </Label>
                <Select
                  value={preferences.language}
                  onValueChange={(value: Preferences["language"]) => updatePreference("language", value)}
                >
                  <SelectTrigger className="glass border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                    <SelectItem value="fr">Français</SelectItem>
                    <SelectItem value="de">Deutsch</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Save Button */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Button onClick={savePreferences} disabled={saving} className="w-full">
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Preferences
              </>
            )}
          </Button>
        </motion.div>
      </div>
    </ScrollArea>
  )
}
