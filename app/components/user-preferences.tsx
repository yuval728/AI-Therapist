"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"
import { apiClient } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { Settings, Save, Loader2, Bell, Shield, Palette } from "lucide-react"
import { motion } from "framer-motion"

interface Preferences {
  theme: string
  notifications: boolean
  crisis_alerts: boolean
  session_reminders: boolean
  privacy_mode: boolean
  language: string
}

export function UserPreferences() {
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    loadPreferences()
  }, [])

  const loadPreferences = async () => {
    try {
      setError(null)
      const prefs = await apiClient.getUserPreferences()
      setPreferences(prefs as Preferences)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to load preferences"
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const savePreferences = async () => {
    if (!preferences) return

    try {
      setSaving(true)
      setError(null)
      await apiClient.updateUserPreferences(preferences)
      toast({
        title: "Preferences saved",
        description: "Your preferences have been updated successfully.",
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to save preferences"
      setError(errorMessage)
      toast({
        title: "Save failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const updatePreference = (key: keyof Preferences, value: any) => {
    if (!preferences) return
    setPreferences({ ...preferences, [key]: value })
  }

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
                <Select value={preferences.theme} onValueChange={(value) => updatePreference("theme", value)}>
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
                <Select value={preferences.language} onValueChange={(value) => updatePreference("language", value)}>
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

        {/* Notifications */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Bell className="w-4 h-4 text-primary" />
                Notifications
              </CardTitle>
              <CardDescription className="text-xs">Manage your notification preferences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notifications" className="text-sm">
                    General Notifications
                  </Label>
                  <p className="text-xs text-muted-foreground">Receive general app notifications</p>
                </div>
                <Switch
                  id="notifications"
                  checked={preferences.notifications}
                  onCheckedChange={(checked) => updatePreference("notifications", checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="crisis-alerts" className="text-sm">
                    Crisis Alerts
                  </Label>
                  <p className="text-xs text-muted-foreground">Important mental health alerts</p>
                </div>
                <Switch
                  id="crisis-alerts"
                  checked={preferences.crisis_alerts}
                  onCheckedChange={(checked) => updatePreference("crisis_alerts", checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="session-reminders" className="text-sm">
                    Session Reminders
                  </Label>
                  <p className="text-xs text-muted-foreground">Reminders for scheduled sessions</p>
                </div>
                <Switch
                  id="session-reminders"
                  checked={preferences.session_reminders}
                  onCheckedChange={(checked) => updatePreference("session_reminders", checked)}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Privacy */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card className="glass border-border/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                Privacy & Security
              </CardTitle>
              <CardDescription className="text-xs">Control your privacy settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="privacy-mode" className="text-sm">
                    Privacy Mode
                  </Label>
                  <p className="text-xs text-muted-foreground">Enhanced privacy for sensitive conversations</p>
                </div>
                <Switch
                  id="privacy-mode"
                  checked={preferences.privacy_mode}
                  onCheckedChange={(checked) => updatePreference("privacy_mode", checked)}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Save Button */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
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
