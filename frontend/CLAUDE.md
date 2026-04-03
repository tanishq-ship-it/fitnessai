# FitnessAI — Project Instructions

## What is this project?
A fitness AI chatbot mobile app built with React Native (Expo) + NativeWind (Tailwind CSS). The app helps users with fitness advice, workout plans, and health guidance through an AI-powered chat interface.

## Tech Stack
- **Framework:** React Native with Expo (SDK 54)
- **Routing:** Expo Router (file-based routing)
- **Styling:** NativeWind v4 (Tailwind CSS classes via `className`)
- **Animations:** react-native-reanimated
- **Gradients:** expo-linear-gradient
- **Blur effects:** expo-blur
- **Icons:** @expo/vector-icons (Ionicons, MaterialIcons, FontAwesome)
- **Haptics:** expo-haptics
- **Language:** TypeScript (strict)

## File Structure
```
frontend/
├── app/                    # Expo Router pages (file-based routing)
│   ├── _layout.tsx         # Root layout
│   ├── (tabs)/             # Tab navigator screens
│   └── (auth)/             # Auth screens (if needed)
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── ui/             # Base UI (Button, Card, Input, Avatar)
│   │   └── chat/           # Chat-specific (MessageBubble, InputBar, TypingIndicator)
│   ├── services/           # API calls and external service integrations
│   ├── hooks/              # Custom React hooks
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Helper functions
│   └── constants/          # App-wide constants (colors, config, prompts)
├── assets/                 # Images, fonts, icons
└── global.css              # Tailwind directives
```

## Design System & UI Guidelines

### Philosophy
Design like ChatGPT / Claude app. Clean, minimal, black & white with aqua as the accent. Chat-first interface.

### Color Palette (defined in tailwind.config.js)
- **Base:** Black (#000000) background, White (#FFFFFF) text
- **Accent:** Aqua (#00D9C0) — the only color, used sparingly for emphasis
- **Surface:** Dark gray (#1A1A1A) for user message bubbles and input areas
- **Text:** White for primary, white/50 for secondary, white/30 for muted
- **Aqua usage:** AI avatar badge, active indicators, send button, brand accents only

### Chat UI Pattern (like ChatGPT/Claude)
- **User messages:** Dark surface bubble, right-aligned, rounded with tail
- **AI messages:** No bubble — plain white text, left-aligned, with small aqua AI badge
- **Input:** Dark surface bar at bottom with rounded input and aqua send button

### Typography
- Headings: `text-2xl font-bold` or `text-3xl font-extrabold`
- Body: `text-base` with `leading-relaxed`
- Captions: `text-sm text-gray-400`
- Use tracking-tight on large headings for premium feel

### Spacing & Layout
- Use consistent padding: `p-4` for screens, `p-3` for cards
- Rounded corners everywhere: `rounded-2xl` for cards, `rounded-full` for buttons/avatars
- Use `gap-3` or `gap-4` between list items
- Safe area padding via `react-native-safe-area-context`

### Components Style Rules
- **Buttons:** Rounded full, gradient backgrounds, shadow-lg, press animation (scale down with reanimated)
- **Cards:** Rounded-2xl, subtle border (border-white/10), backdrop blur when overlaying
- **Inputs:** Rounded-xl, dark surface bg, subtle border, focus ring effect
- **Chat bubbles:** User = gradient primary (right-aligned), Bot = dark surface (left-aligned), rounded-2xl with tail
- **Lists:** Use separators sparingly, prefer spacing
- **Loading states:** Skeleton loaders or animated dots, never empty screens
- **Transitions:** Use reanimated for enter/exit animations on screens and components

### Shadows & Depth
- Cards: `shadow-lg shadow-black/20`
- Floating buttons: `shadow-xl shadow-primary/30`
- Use blur overlays for modals (expo-blur)

### Icons
- Use Ionicons from @expo/vector-icons as the primary icon set
- Size 24 for standard, 20 for compact, 28 for navigation
- Always match icon color to surrounding text color

### Animations (react-native-reanimated)
- Button press: scale to 0.95 with spring config
- Screen transitions: fade + slide up
- Chat messages: fade in + slide up from bottom
- Typing indicator: animated dots
- Pull to refresh: custom animated header

### Dark Mode First
- Default to dark mode — it looks more premium for fitness apps
- Support light mode as secondary
- Use `bg-black` / `bg-white` with NativeWind dark: prefix

## Code Conventions
- Use functional components with hooks
- Use TypeScript interfaces for all props and data types
- Name files in kebab-case: `message-bubble.tsx`, `use-chat.ts`
- Export components as default exports
- Keep components under 150 lines — extract sub-components when needed
- Use custom hooks to separate business logic from UI
- API keys go in environment variables, NEVER in source code

## LLM / Chat Integration
- API calls go through a backend proxy (never call LLM APIs directly from the app)
- Support streaming responses for real-time typing effect
- System prompt should establish the AI as a knowledgeable fitness coach
- Store chat history locally with AsyncStorage or SQLite
- Handle errors gracefully with user-friendly messages

## When building new features:
1. Create the types first in `src/types/`
2. Build the service/API layer in `src/services/`
3. Create a custom hook in `src/hooks/` for business logic
4. Build UI components in `src/components/`
5. Compose everything in the screen file under `app/`
