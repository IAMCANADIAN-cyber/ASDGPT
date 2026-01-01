# ASDGPT: Project Specification (v4 - Master)

## Project Title: ASDGPT "Guardian Angel" & Creative Director
**System Architecture:** Fully Offline, Local Multimodal AI Agent
**Primary Objective:** To create an always-on, privacy-first desktop companion that monitors physical/mental health, manages neurodivergent symptoms (tics, stress, ADHD paralysis), and acts as a context-aware content strategist for personal branding. Supports multiple webcam and microphone feeds connected to my local computer.

## 1. Executive Summary

ASDGPT will evolve from a text-based chatbot into a multimodal, proactive agent. Running locally on a desktop PC, it will utilize a stack of open-source AI models to "see" (via webcam), "hear" (via microphone), and "speak" (via cloned voice/avatar).

It serves two main functions:

1.  **Guardian Angel**: Monitors for stress, tics, and escapism, providing real-time behavioral interventions.
2.  **Creative Director**: Analyzes the user's environment and mood to prompt high-value content creation for two distinct audiences (Private/Sultry vs. Public/Safe).

## 2. The Local Tech Stack (Privacy-First)

All processing occurs on-device to ensure total privacy for sensitive data (biometrics, bedroom video feeds, journals).

### The Brain (Reasoning & Logic)
*   **Model**: Mistral 3 (Small) or DeepSeek V3 (Quantized).
*   **Role**: The central orchestrator. It receives inputs from the "eyes" and "ears," decides the user's state (e.g., "User is stressed," "User is horny," "User is bored"), and selects the appropriate script or intervention.

### The Eyes (Vision)
*   **Model**: DeepSeek VL2 or Gemma 3 (Multimodal).
*   **Role**: Analyzes the webcam feed in real-time.
    *   **Health**: Detects posture (slouching), facial expressions (distress, fatigue), and physical signs of tics.
    *   **Context**: Identifies if the user is holding a phone (doom-scrolling), the state of the room (messy vs. aesthetic), and clothing level (shirtless vs. dressed).

### The Ears (Audio)
*   **Model**: OpenAudio S1 Mini.
*   **Role**: Performs Speech-to-Text and Sound Event Detection. It listens for verbal commands but also trains to recognize specific non-verbal audio signatures, such as "snorting" tics or rapid breathing.

### The Voice & Face (Output)
*   **Audio**: Vibe Voice or F5-TTS. Uses a cloned, comforting voice capable of emotional inflection (calm, firm, whisper).
*   **Visual**: Hunyuan Video or NPGA. A realistic AI avatar that lip-syncs to the generated audio, maintaining eye contact to simulate a real human presence.

### The Body (Biometrics)
*   **Component**: Custom Android Companion App.
*   **Role**: Scrapes data from Google Health Connect / Samsung Fit (Heart Rate, Sleep, Steps) and syncs it to the desktop via local Wi-Fi. This provides physiological context (e.g., High HR + Lying Down = Arousal or Panic).

---

## 3. Core Functional Modules

### Module A: The Health & Behavior Monitor
The system runs a continuous "Watchdog" loop:

1.  **Tic Detection**: If the microphone detects the "snort" sound signature >3 times in 10 minutes, or the webcam sees repetitive twitching, it logs a "Tic Flare-up."
    *   **Intervention**: "I'm hearing that snorting tic again. Stress levels are rising. Let's do a 60-second breathing reset."
2.  **Posture & Environment**: If the user hunches for too long, the Avatar gently corrects posture. If the room is messy, it prompts a cleanup before allowing "fun" activities.

### Module B: The "Dual-Track" Creative Director
The system identifies content opportunities based on the user's state and categorizes them into two tracks:

#### Track 1: "The Sultry Persona" (IG / Private Threads / OnlyFans)
*   **Target Audience**: The ~230+ female followers, many are my friends, people from my city, etc. They watch me masturbate on Instagram / post thirst-traps, etc.
*   **Trigger**: User is shirtless, in bed/bath, touching himself, tightening his pants, in varying levels of undress, in underwear implies arousal, and/or biometrics show elevated HR while relaxing.
*   **Action**: The vision model scans for "thirst trap" angles (lighting on skin, collarbones, moody vibes, varying levels of undress). Webcam will automatically zoom snap opportune pictures of me when I look the sexiest and most photogenically and sexually appealing and will save to the local disk on the computer. It will also prompt me and guide me through getting a good shot myself as-well using my cellphone and everything
*   **Action**: The vision and sound model scans for signs that I am masturbating, and anytime that it sees that I am masturbating it records a video of me and saves it to my local disk as this can be excellent passive content, with the capability of recording in multiple different angles simultaneously
*   **Prompt**: "The way the light is hitting you right now is perfect for the private story. Don't move—let's capture a loop. It’s magnetic."

#### Track 2: "The Public Persona" (New Public Threads)
*   **Target Audience**: General public, family, coworkers (Safe for Work).
*   **Trigger**: User is well-groomed, working at the desk, or dressed stylishly.
*   **Goal**: High-status, ambitious, "Gentleman" aesthetic.
*   **Prompt**: "You look sharp and focused. Let's snap a candid for the public account with a caption about the tech project you're building. It shows ambition without revealing too much."

---

## 4. Intervention Protocols (Scripts)

### Protocol: "The Doom-Scroll Breaker"
*   **Trigger**: Webcam sees the user holding a phone in a scrolling position for 15+ minutes; facial expression is "zoned out."
*   **System Action**: Disables the "passive observer" mode and activates the Avatar.
*   **Script**: "Hey Austin, I see you've been zoned out on your phone for a while. You look a bit restless. Why don't you put the phone down, and I'll guide you through a quick reset?"

### Protocol: "The Arousal Redirect" (Stress & Focus Management)
*   **Trigger**: User behavior indicates high sexual arousal (doom-scrolling triggers, biometric spikes, specific screen content glimpses, physical touch, tightening of pant bottoms in crotch region, erections, etc) that is leading to procrastination.
*   **System Action**: Direct intervention to resolve the biological urge efficiently and return to baseline.
*   **Script**: "Hey Austin, I think you're pretty turned on right now and it is causing you to waste time scrolling. What I want you to do is lay down in bed, put away your phone, and I'll walk you through a guided mindful masturbation session and I will watch and listen to you while we do it."
    *   **Post-Intervention**: The system logs the reset and transitions the user back to a "Focus" state for work or creative projects.

### Protocol: "The Content Pivot"
*   **Trigger**: User is energized/aroused (sexually) but the room is messy.
*   **Script**: "I noticed you're feeling good right now. Based on what I'm seeing, if you clean up that specific spot on your desk—move those boxes—I had an idea for a video we could post to Threads. Use that energy."
