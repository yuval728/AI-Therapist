"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DemoBanner } from "./demo-banner"
import { useAuth } from "@/hooks/use-auth"
import { Loader2, Mail, Lock, User, Eye, EyeOff } from "lucide-react"
import { motion } from "framer-motion"
import { apiClient } from "@/lib/api"
import { signInSchema, signUpSchema, validateData } from "@/lib/validation-schemas"
import { handleValidationError } from "@/lib/error-handler"

interface AuthFormProps {
  mode: "login" | "signup"
  onToggleMode: () => void
  onSuccess: () => void
}

export function AuthForm({ mode, onToggleMode, onSuccess }: AuthFormProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [fullName, setFullName] = useState("")
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [formSuccess, setFormSuccess] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const { login, signup } = useAuth()

  const validateForm = (): { isValid: boolean; errors: string[] } => {
    setFieldErrors({})

    if (mode === "login") {
      const result = validateData(signInSchema, { email, password })
      if (!result.success) {
        const errors = result.errors || []
        handleValidationError(new Error(errors.join(", ")), {
          component: "AuthForm",
          action: "login_validation",
        })
        return { isValid: false, errors }
      }
      return { isValid: true, errors: [] }
    } else {
      const result = validateData(signUpSchema, {
        email,
        password,
        confirmPassword,
        fullName: fullName || undefined,
        termsAccepted,
      })
      if (!result.success) {
        const errors = result.errors || []
        handleValidationError(new Error(errors.join(", ")), {
          component: "AuthForm",
          action: "signup_validation",
        })
        return { isValid: false, errors }
      }
      return { isValid: true, errors: [] }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setFormSuccess(null)
    setFieldErrors({})

    const validation = validateForm()
    if (!validation.isValid) {
      setFormError(validation.errors[0] || "Please check your input")
      return
    }

    setIsSubmitting(true)

    try {
      if (mode === "login") {
        await login(email, password)
        setFormSuccess("Login successful! Redirecting...")
        // Small delay to ensure auth state is fully updated
        setTimeout(() => {
          onSuccess()
        }, 100)
      } else {
        await signup(email, password, fullName || undefined)
        setFormSuccess("Account created successfully. Please sign in.")
        resetSignupForm()
        onToggleMode()
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Authentication failed"

      // Provide more specific error messages
      let userFriendlyMessage = errorMessage
      if (errorMessage.includes("invalid credentials") || errorMessage.includes("unauthorized")) {
        userFriendlyMessage = "Invalid email or password. Please try again."
      } else if (errorMessage.includes("user already exists") || errorMessage.includes("email already")) {
        userFriendlyMessage = "An account with this email already exists. Please sign in instead."
      } else if (errorMessage.includes("network") || errorMessage.includes("fetch")) {
        userFriendlyMessage = "Network error. Please check your connection and try again."
      } else if (errorMessage.includes("rate limit")) {
        userFriendlyMessage = "Too many attempts. Please wait a moment before trying again."
      }

      setFormError(userFriendlyMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetSignupForm = () => {
    setPassword("")
    setConfirmPassword("")
    setTermsAccepted(false)
    setFullName("")
    setFieldErrors({})
  }

  const handleFieldChange = (field: string, value: string | boolean) => {
    // Clear field-specific error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: "" }))
    }

    switch (field) {
      case "email":
        setEmail(value as string)
        break
      case "password":
        setPassword(value as string)
        break
      case "confirmPassword":
        setConfirmPassword(value as string)
        break
      case "fullName":
        setFullName(value as string)
        break
      case "termsAccepted":
        setTermsAccepted(value as boolean)
        break
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-secondary/20">
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="w-full max-w-md"
      >
        {apiClient.isDemoMode() && <DemoBanner />}

        <Card className="w-full max-w-md glass-strong shadow-2xl border-border/30 backdrop-blur-xl">
          <CardHeader className="text-center space-y-2">
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.2, duration: 0.6, type: "spring", stiffness: 200 }}
              className="mx-auto w-16 h-16 bg-gradient-to-br from-primary/10 to-primary/5 rounded-full flex items-center justify-center mb-4 shadow-lg"
            >
              <User className="w-8 h-8 text-primary" />
            </motion.div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
              <CardTitle className="text-2xl font-manrope text-foreground">
                {mode === "login" ? "Welcome Back" : "Create Account"}
              </CardTitle>
              <CardDescription className="text-muted-foreground mt-2">
                {mode === "login" ? "Sign in to continue your journey" : "Start your mental wellness journey today"}
              </CardDescription>
            </motion.div>
          </CardHeader>

          <CardContent>
            <motion.form
              onSubmit={handleSubmit}
              className="space-y-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <div className="space-y-4">
                {mode === "signup" && (
                  <motion.div
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.45 }}
                    className="relative group"
                  >
                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                    <Input
                      type="text"
                      placeholder="Full name (optional)"
                      value={fullName}
                      onChange={(e) => handleFieldChange("fullName", e.target.value)}
                      className={`pl-10 h-12 glass border-border/50 focus:border-primary/50 transition-all duration-300 focus:shadow-lg focus:shadow-primary/10 ${
                        fieldErrors.fullName ? "border-destructive/50" : ""
                      }`}
                    />
                    {fieldErrors.fullName && <p className="text-xs text-destructive mt-1">{fieldErrors.fullName}</p>}
                  </motion.div>
                )}
                <motion.div
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="relative group"
                >
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                  <Input
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => handleFieldChange("email", e.target.value)}
                    className={`pl-10 h-12 glass border-border/50 focus:border-primary/50 transition-all duration-300 focus:shadow-lg focus:shadow-primary/10 ${
                      fieldErrors.email ? "border-destructive/50" : ""
                    }`}
                    required
                  />
                  {fieldErrors.email && <p className="text-xs text-destructive mt-1">{fieldErrors.email}</p>}
                </motion.div>

                <motion.div
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.6 }}
                  className="relative group"
                >
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => handleFieldChange("password", e.target.value)}
                    className={`pl-10 pr-10 h-12 glass border-border/50 focus:border-primary/50 transition-all duration-300 focus:shadow-lg focus:shadow-primary/10 ${
                      fieldErrors.password ? "border-destructive/50" : ""
                    }`}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-primary transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  {fieldErrors.password && <p className="text-xs text-destructive mt-1">{fieldErrors.password}</p>}
                </motion.div>

                {mode === "signup" && (
                  <motion.div
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.7 }}
                    className="relative group"
                  >
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                    <Input
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Confirm your password"
                      value={confirmPassword}
                      onChange={(e) => handleFieldChange("confirmPassword", e.target.value)}
                      className={`pl-10 pr-10 h-12 glass border-border/50 focus:border-primary/50 transition-all duration-300 focus:shadow-lg focus:shadow-primary/10 ${
                        fieldErrors.confirmPassword ? "border-destructive/50" : ""
                      }`}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-primary transition-colors"
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                    {fieldErrors.confirmPassword && (
                      <p className="text-xs text-destructive mt-1">{fieldErrors.confirmPassword}</p>
                    )}
                  </motion.div>
                )}

                {mode === "signup" && (
                  <motion.label
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.75 }}
                    className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none"
                  >
                    <input
                      type="checkbox"
                      checked={termsAccepted}
                      onChange={(e) => handleFieldChange("termsAccepted", e.target.checked)}
                      className={fieldErrors.termsAccepted ? "border-destructive" : ""}
                    />
                    I accept the Terms of Service
                    {fieldErrors.termsAccepted && (
                      <p className="text-xs text-destructive ml-2">{fieldErrors.termsAccepted}</p>
                    )}
                  </motion.label>
                )}
              </div>

              {formError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm"
                >
                  {formError}
                </motion.div>
              )}

              {formSuccess && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-emerald-600/10 border border-emerald-600/20 text-emerald-600 text-sm"
                >
                  {formSuccess}
                </motion.div>
              )}

              <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.8 }}>
                <Button
                  type="submit"
                  className="w-full h-12 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-primary-foreground font-medium transition-all duration-300 shadow-lg hover:shadow-xl relative overflow-hidden"
                  disabled={isSubmitting}
                >
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300"
                    whileHover={{ x: ["-100%", "100%"] }}
                    transition={{ duration: 0.6 }}
                  />
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {mode === "login" ? "Signing In..." : "Creating Account..."}
                    </>
                  ) : mode === "login" ? (
                    "Sign In"
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </motion.div>
            </motion.form>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
              className="mt-6 text-center"
            >
              <p className="text-sm text-muted-foreground">
                {mode === "login" ? "Don't have an account?" : "Already have an account?"}
                <button
                  type="button"
                  onClick={onToggleMode}
                  className="ml-2 text-primary hover:text-primary/80 font-medium transition-colors hover:underline"
                >
                  {mode === "login" ? "Sign Up" : "Sign In"}
                </button>
              </p>
            </motion.div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
