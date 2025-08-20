interface ChatMessage {
  sender: "user" | "therapist"
  message: string
  timestamp: string
}

interface User {
  id: string
  user_id: string
  email: string
}

// Mock user data
export const mockUser: User = {
  id: "demo-user-123",
  user_id: "demo-user-123",
  email: "demo@example.com",
}

// Mock chat history
export const mockChatHistory: ChatMessage[] = [
  {
    sender: "therapist",
    message:
      "Hello! I'm your AI therapist. I'm here to provide a safe, supportive space for you to explore your thoughts and feelings. How are you doing today?",
    timestamp: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    sender: "user",
    message: "Hi, I've been feeling a bit overwhelmed lately with work and personal life.",
    timestamp: new Date(Date.now() - 3500000).toISOString(),
  },
  {
    sender: "therapist",
    message:
      "I understand that feeling overwhelmed can be really challenging. It sounds like you're juggling quite a bit right now. Can you tell me more about what specifically is making you feel this way?",
    timestamp: new Date(Date.now() - 3400000).toISOString(),
  },
]

// Therapeutic responses for demo mode
export const mockTherapistResponses = [
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
]

// Function to get a random therapeutic response
export function getRandomTherapistResponse(): string {
  return mockTherapistResponses[Math.floor(Math.random() * mockTherapistResponses.length)]
}

// Simulate API delay
export function simulateDelay(ms = 1000): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
