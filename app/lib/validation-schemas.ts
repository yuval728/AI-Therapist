import { z } from "zod"

// Auth schemas
export const signInSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

export const signUpSchema = z
  .object({
    email: z.string().email("Please enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/[0-9]/, "Password must contain at least one number"),
    confirmPassword: z.string(),
    fullName: z.string().optional(),
    termsAccepted: z.boolean().refine((val) => val === true, "You must accept the Terms of Service"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  })

// Profile schemas
export const profileUpdateSchema = z.object({
  full_name: z.string().min(1, "Full name is required").max(100, "Full name is too long"),
  email: z.string().email("Please enter a valid email address"),
})

export const preferencesSchema = z.object({
  theme: z.enum(["light", "dark", "system"]).optional(),
  notifications: z.boolean().optional(),
  crisis_alerts: z.boolean().optional(),
  session_reminders: z.boolean().optional(),
  privacy_mode: z.boolean().optional(),
  language: z.string().min(2).max(5).optional(),
})

// Session schemas
export const sessionCreateSchema = z.object({
  emotion: z.string().min(1).max(50).optional(),
  crisis_level: z.number().min(0).max(10).optional(),
  metadata: z.record(z.any()).optional(),
})

// Message schemas
export const messageSchema = z.object({
  content: z.string().min(1, "Message cannot be empty").max(2000, "Message is too long"),
})

// Validation helper
export const validateData = (schema, data) => {
  try {
    const validData = schema.parse(data)
    return { success: true, data: validData }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        success: false,
        errors: error.errors.map((err) => err.message),
      }
    }
    return {
      success: false,
      errors: ["Validation failed"],
    }
  }
}

export type SignInData = z.infer<typeof signInSchema>
export type SignUpData = z.infer<typeof signUpSchema>
export type ProfileUpdateData = z.infer<typeof profileUpdateSchema>
export type PreferencesData = z.infer<typeof preferencesSchema>
export type SessionCreateData = z.infer<typeof sessionCreateSchema>
export type MessageData = z.infer<typeof messageSchema>
