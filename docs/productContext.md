# Product Context - Rashigo

## Platform Overview
Rashigo is a **Gamified Social Platform** combining real-time communication with competitive gaming features. It functions as a native game launcher similar to Discord or Steam.

## Core Features

### 1. Communication System
- **Text Channels**: Real-time chat within servers via WebSocket
- **Voice Channels**: WebRTC-powered voice with COTURN support
- **Private Messages**: Direct messaging between users
- **Server System**: Create and manage community servers with roles

### 2. Gaming Platform
- **Mini-Games**: Dice Wars and extensible game framework
- **Game Lobbies**: Public/private rooms with matchmaking
- **Live Gameplay**: WebSocket-powered real-time game sessions

### 3. Ranking & Gamification
- **Rank Points**: Earned through gameplay performance
- **Leaderboards**: Global and per-game rankings
- **Player Stats**: Total games, wins, losses, win rate

### 4. User System
- **Custom Profiles**: Bio, avatar, status message
- **Verification**: Email verification support
- **Security**: Bot detection, profanity filtering, Turnstile CAPTCHA

---

## Design Standards

### Visual Style: Clean Modern Dark UI
Inspired by Discord and Linear.app - professional yet gamified.

### Color Palette
Token,Value,Usage
--bg-primary,#0F172A,Main background (Deep Slate)
--bg-secondary,#1E293B,"Sidebar, cards (Lighter Navy)"
--bg-surface,#334155,"Inputs, hover states"
--accent-primary,#38BDF8,Primary accent (Sky Blue)
--accent-secondary,#6366F1,Secondary accent (Indigo)
--text-primary,#F8FAFC,Main text (Off-white)
--text-secondary,#94A3B8,Muted text (Slate gray)
--border,"rgba(148, 163, 184, 0.1)",Subtle borders

### Typography
- **Font Family**: Inter (Google Fonts)
- **Weights**: 400 (body), 500 (medium), 600 (semibold), 700 (bold)

### Iconography
- **Icon Set**: Lucide Icons (SVG)
- **NO EMOJIS**: Strictly prohibited in UI - use icons only
- **Icon Size**: 20-24px for navigation, 16-18px for inline

### Spacing
- **Base Unit**: 4px
- **Sidebar Width**: 72px
- **Card Border Radius**: 12-16px

### Interaction
- **Transitions**: 0.2s ease
- **Hover States**: Background shift + accent color
- **Active States**: Accent color with indicator bar
