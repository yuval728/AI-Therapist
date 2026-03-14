export interface ChatMessage {
  sender: "user" | "therapist"
  message: string
  timestamp: string
}

export interface MockUser {
  id: string
  user_id: string
  email: string
}

export const mockUser: MockUser = {
  id: "demo-user-123",
  user_id: "demo-user-123",
  email: "demo@example.com",
}

const createMockMessage = (sender: ChatMessage['sender'], message: string, hoursAgo: number): ChatMessage => ({
  sender,
  message,
  timestamp: new Date(Date.now() - hoursAgo * 3600000).toISOString(),
})

export const mockChatHistory: ChatMessage[] = [
  createMockMessage(
    "therapist",
    "Hello! I'm your AI therapist. I'm here to provide a safe, supportive space for you to explore your thoughts and feelings. How are you doing today?",
    1
  ),
  createMockMessage(
    "user",
    "Hi, I've been feeling a bit overwhelmed lately with work and personal life.",
    0.97
  ),
  createMockMessage(
    "therapist",
    "I understand that feeling overwhelmed can be really challenging. It sounds like you're juggling quite a bit right now. Can you tell me more about what specifically is making you feel this way?",
    0.94
  ),
]

const mockTherapistResponses = [
  "That sounds really difficult. It takes courage to share these feelings. Can you tell me more about what that experience was like for you?",
  "I hear you, and I want you to know that what you're feeling is completely valid. Many people struggle with similar challenges.",
  "It sounds like you're being really hard on yourself. What would you say to a friend who was going through the same thing?",
  "That's a significant realization. How does it feel to acknowledge that about yourself?",
  "I notice you mentioned feeling [emotion]. Can you help me understand what that feeling is like for you?",
  "It seems like this situation is weighing heavily on you. What kind of support do you think would be most helpful right now?",
  "You've shown a lot of strength in dealing with this. What coping strategies have you found helpful in the past?",
  "That's a really thoughtful way to look at it. How might you apply this insight to your current situation?",
  "I can sense the pain in what you're sharing. Remember that healing isn't linear, and it's okay to take things one step at a time.",
  "What you're describing sounds like a pattern. Have you noticed this happening in other areas of your life too?",
] as const

export function getRandomTherapistResponse(): string {
  const randomIndex = Math.floor(Math.random() * mockTherapistResponses.length)
  return mockTherapistResponses[randomIndex]
}

export function simulateDelay(ms = 1000): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const DEMO_CONFIG = {
  DEFAULT_DELAY: 1000,
  TYPING_DELAY: 50,
  MAX_RESPONSE_DELAY: 3000,
} as const
