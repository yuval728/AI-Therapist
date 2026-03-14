import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Manrope } from "next/font/google"
import "./globals.css"
import { AppErrorBoundary } from "@/components/error-boundary"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/toaster"

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
})

const manrope = Manrope({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-manrope",
})

export const metadata: Metadata = {
  title: "AI Therapist - Your Mental Health Companion",
  description: "A safe space for mental health conversations with AI support",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${manrope.variable} antialiased`} suppressHydrationWarning>
      <body
        className="min-h-screen bg-gradient-to-br from-background via-background to-secondary/20"
        suppressHydrationWarning
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange={false}
        >
          <AppErrorBoundary>
            {children}
            <Toaster />
          </AppErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}
