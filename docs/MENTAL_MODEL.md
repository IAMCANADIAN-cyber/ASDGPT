# ASDGPT Mental Model & Design Specification

This document outlines the core mental model, state definitions, and intervention strategies for ASDGPT. It serves as the engineering spec for the system's logic.

## Mental model (so the system stays sane as it grows)

Think of ASDGPT as 4 layers:

1.  **Sensors → Features**
    Raw audio/video become features (speech rate, posture changes, fidget intensity, etc.), plus confidence.
2.  **Features → State estimation**
    A "state engine" that outputs things like: baseline, focused, distracted, overloaded, shutdown-y, dysregulated, fatigued, low-mood, pain-suspected, etc. (not "you have X disease").
3.  **State → Intervention selection**
    A policy that chooses the smallest effective nudge: micro-break, hydration, sensory reduction, task split, grounding exercise, "step outside," "message someone," etc.
4.  **Learning loop (personalization)**
    Your feedback hotkeys (helpful/unhelpful) tune thresholds, timing, and tone.

This structure prevents the LLM from becoming the "source of truth" and keeps it as a coach/translator sitting on top of measurable signals.

---

## What it can "check for" (high-impact signals for you, specifically)

### A) Autism overload / burnout trajectory signals (co-regulation targets)

**Video features**
*   Reduced gaze stability / more "stare through" moments
*   Increase in self-soothing/stimming motion (hands, rocking, leg bounce)
*   Postural collapse (shoulders forward, head down) or "freeze posture"
*   Facial tension clusters (jaw clench, brow knit) relative to your baseline

**Audio features**
*   Shorter utterances, more pauses, less prosody variation
*   Sigh frequency, breathiness, throat clearing (often tracks stress/fatigue)
*   Irritability markers: clipped responses, louder consonants, sharper onset

**State outputs**
*   Overload rising (fast changes from baseline)
*   Shutdown drift (low motion + low speech + longer response latency)
*   Meltdown risk (high arousal + escalating motion + escalating voice intensity)

**Interventions that fit autism/ADHD realities**
*   "Reduce input" suggestions (lights down, noise off, headphones)
*   "Body-first" regulation: temperature change, pressure, water, short walk
*   "Permission scripts" (your brain likes structured authority): 90-second reset, then resume.

### B) ADHD focus architecture (hyperfocus vs derailment)

**Signals**
*   **Hyperfocus**: long uninterrupted activity blocks + minimal posture change + reduced blinking + very low speech
*   **Derailment**: rapid app switching (if you add OS telemetry), restless movement, fragmented speech, repeated "start/stop" behaviors

**Interventions**
*   **Hyperfocus guardrails**: scheduled micro-breaks that don’t break momentum (e.g., "stand + sip + 3 breaths, 45 seconds")
*   **Derailment**: "two-step re-entry" (write next 1 action, then do 2 minutes)

### C) Depression / low-mood drift (without being cringe)

**Signals**
*   Extended inactivity + low vocal energy + reduced facial animation over hours/days
*   "Cognitive friction": repeated task avoidance loops (if OS telemetry is added)

**Interventions**
*   **Low-activation nudges**: tiny wins (shower, laundry, outside sunlight)
*   **Social micro-touch**: prompt a low-stakes message to someone safe
*   "Narrative reframing" only when the model is confident you’re receptive (avoid lecturing)

### D) Sleep / nighttime risk monitoring (non-diagnostic but useful)

Given your history (sleep apnea + episodes that feel like choking/reflux), a mic/webcam system can still be valuable as a sentinel:

**Checks**
*   Snore intensity changes over baseline
*   Long silence + motionless + then sudden gasps (pattern flag, not a diagnosis)
*   Repeated cough/throat-clear clusters after lying down (reflux-likely pattern flag)

**Prompts**
*   "Sit up / water / antacid if prescribed / check CPAP seal / consider side position"
*   "If you experience chest pain, fainting, blue lips, severe shortness of breath → emergency services" (hard-coded escalation rules)

---

## Expansions that will feel "mind-blowing" in practice

### 1) Personal baseline modeling (the secret sauce)
Add a concept of:
*   Time-of-day baselines (your "normal" at 9am ≠ 9pm)
*   Context baselines (work mode vs chill mode)
*   Rolling calibration windows (e.g., "learn my neutral face/voice for 2 minutes" hotkey)
This turns the system from "generic emotion detector" into Austin-detector.

### 2) Multi-signal "reasoning" without pretending to be a doctor
Instead of "you have X," output:
*   Top 3 plausible contributors (stress, fatigue, hunger, sensory overload, reflux-like pattern, anxiety spike)
*   What evidence supports each (features + trend)
*   What quick test reduces uncertainty ("drink water + 2 min quiet; does throat sensation drop?")
This is the right level of "medical-ish usefulness" without crossing into fake certainty.

### 3) Intervention taxonomy + a policy engine (so it doesn’t annoy you)
Create categories and rules like:
*   **Micro-regulation (≤90s)**: breathe, stretch, water, posture reset
*   **Sensory control (≤5m)**: lights, sound, temperature, clothing, pressure
*   **Cognitive control (≤5m)**: pick next action, remove 1 distraction, rewrite task smaller
*   **Social support**: prompt a message, schedule a check-in
*   **Escalation**: "stop what you’re doing" + "seek human help" rules

Then implement a "minimum effective dose" policy:
*   Don’t repeat the same intervention within X minutes unless the state worsens.
*   If you mark "unhelpful," reduce frequency and/or change tone, not just the content.

### 4) A "Crisis GPT" playbook that’s actually operational
Build a small local knowledge base that includes:
*   Your known patterns (shutdown signs, what helps, what makes it worse)
*   Your preferred scripts ("tell me like Picard," "tell me like Harvey," "just facts")
*   The ability for the LLM to speak verbally (out loud to me) and for me to speak out loud back to it – aka voice communication – LLM will monitor me at all times through my desktop webcam, and microphone – it will pick up issues and course correct me throughout the day – it will monitor my health and wellbeing and perform sentiment analysis. ASDGPT does this by speaking to a local LLM on my desktop that I can point to via a simple UI interface (For example placing http://127.0.0.1:1234/ in)

The LLM’s job becomes: pick the right playbook card and speak it well.

---

## Signals / States / Interventions Matrix

Below is a Signals / States / Interventions matrix you can treat like an engineering spec for ASDGPT. It’s designed to be:
*   **multimodal** (cam + mic + optional OS telemetry + optional self-report)
*   **personalizable** (baseline learning + your hotkey feedback loop)
*   **actionable** (clear triggers → clear next step)
*   **low-annoyance** (cooldowns, confidence gates, "minimum effective nudge")

### Core design: 5 internal dimensions (makes "states" consistent)
Instead of dozens of brittle states, model five continuously-scored dimensions and then map them to states.

**Dimensions (0–100):**
1.  **Arousal** (physiological activation: calm → keyed up)
2.  **Overload** (sensory/cognitive load: manageable → too much)
3.  **Focus lock** (scattered → hyperfocused)
4.  **Energy** (alert → depleted/drowsy)
5.  **Mood valence** (positive/neutral → negative)

A "state" is just a named region in this 5D space (plus context like time-of-day).

### Signal layers (what ASDGPT can observe)

**A) Camera-derived features**
*   Motion intensity (optical flow / movement per minute)
*   Fidget rate (repetitive small movements vs baseline)
*   Posture (upright/lean; head down; slumped)
*   Freeze (very low motion for long periods)
*   Facial tension proxies (jaw/brow tension heuristics; "tight face" vs baseline)
*   Blink rate / gaze drift (rough fatigue markers)

**B) Microphone-derived features**
*   Speech rate (words/min or syllables/sec)
*   Volume / intensity
*   Pitch variability (monotone vs animated)
*   Pause ratio (silence gaps, latency to respond)
*   Breath markers (sigh count; rapid breath; breath-hold-like gaps)
*   Non-speech events (cough/throat clear clusters)

**C) Optional OS / workflow telemetry (high-leverage)**
*   Active window/app + switching frequency
*   Keyboard/mouse activity (burst vs idle)
*   Meeting detection (calendar + mic "speech present")
*   Time since break
*   Late-night usage pattern

**D) Optional self-report (best "ground truth")**
*   1–10 quick sliders: stress, overload, energy, mood, pain/discomfort
*   One-tap tags: hungry, thirsty, headache, refluxy, anxious

### Confidence & gating rules (anti-annoyance backbone)
*   **Hard rule**: don’t intervene off a single cue. Require 2+ modalities OR 1 modality + strong trend.
*   **Confidence levels**:
    *   Low: log only
    *   Medium: gentle nudge (one sentence)
    *   High: offer choice + prompt for quick self-report
*   **Cooldown**: after any intervention, wait 10–30 min depending on severity unless state worsens sharply.
*   **Variation**: don’t repeat the same intervention type twice in a row unless user marked it "helpful."

---

### Signals / States / Interventions Matrix
Each state below includes: Definition, Primary signals, Disconfirmers, Trigger rule, and Intervention ladder.

#### S0 — Baseline / Regulated
*   **Definition**: Arousal, overload, energy stable near baseline.
*   **Primary signals**: Normal speech prosody + normal motion + normal posture (relative baseline)
*   **Trigger rule**: Default when no other state crosses thresholds.
*   **Interventions**: None. (Occasional "positive reinforcement" only if you want it; otherwise avoid.)

#### S1 — Flow (healthy focus)
*   **Definition**: Focus lock moderately high, arousal manageable, energy stable.
*   **Signals**:
    *   Reduced speech + stable posture + steady keyboard/mouse (optional)
    *   Low fidgeting, low stress markers
*   **Disconfirmers**: Rising tension, rising fidget, rising breath markers
*   **Trigger**: Focus lock ↑ AND overload not rising AND arousal not rising
*   **Interventions**:
    1.  Nudge: "You’re in flow. Want a 30s posture+water reset to protect it?"
    2.  Choice: "Keep going / 30s reset / set a 20-min check-in"
    3.  Escalate only if energy drops: "You’re fading—micro-break now prevents crash."

#### S2 — Hyperfocus lock (productive but risky)
*   **Definition**: Focus lock very high + break neglect risk + body needs ignored.
*   **Signals (need 2+)**:
    *   Very low motion + sustained input activity (OS) for 60–120+ min
    *   Reduced blinking / fixed posture
    *   No speech, no environment change
*   **Disconfirmers**: Frequent movement, normal breaks, normal speech
*   **Trigger**: Focus lock > threshold for duration AND time-since-break > threshold
*   **Interventions**:
    1.  Nudge: "Bookmark your current thought in 1 sentence—then stand 60 seconds."
    2.  Choice: "60s stand / water+snack / set a 25-min timer"
    3.  Escalate: "If you ignore this twice, I’ll switch to ‘protective mode’ and remind again in 10."

#### S3 — Mild stress (early warning)
*   **Definition**: Arousal rising but still controllable.
*   **Signals**:
    *   Slightly faster speech, slightly higher volume
    *   Mild facial tension + fidgeting uptick
    *   More app switching (optional)
*   **Disconfirmers**: Calm speech + stable posture + stable motion trend
*   **Trigger**: Arousal ↑ trend for 5–10 min with 2+ cues
*   **Interventions**:
    1.  Nudge: "Stress rising. 3 slow exhales?"
    2.  Choice: "Breath / quick stretch / reduce noise"
    3.  If repeated: prompt a 1–10 stress slider + log trigger context

#### S4 — High stress / dysregulation onset
*   **Definition**: Arousal high + control slipping.
*   **Signals (2+ modalities strongly)**:
    *   Speech rate spikes + sharp volume
    *   Pacing / agitated motion + tight face
    *   Breath markers increase (sighs/rapid)
*   **Disconfirmers**: Stable prosody, stable motion, normal breathing
*   **Trigger**: Arousal above threshold for 2–5 min AND overload rising OR focus fragmenting
*   **Interventions**:
    1.  Nudge: "Pause. Drop shoulders. Exhale long."
    2.  Choice: "Quiet mode (5 min) / short walk / cold water"
    3.  Escalate: "I think you’re nearing overload. Want me to switch to low-stim mode + block prompts for 10?"

#### S5 — Overload (sensory/cognitive)
*   **Definition**: Overload high; tolerance low.
*   **Signals**:
    *   Irritability + shorter phrases
    *   Increased self-soothing movements
    *   Avoidant gaze / head down
    *   Environmental noise + multitask pile (if measurable)
*   **Disconfirmers**: Returning prosody + relaxed motion
*   **Trigger**: Overload trend up for 10–20 min OR sudden jump after stimulus event
*   **Interventions**:
    1.  Nudge: "Overload. Reduce input first."
    2.  Choice: "Dim/quiet / headphones / single-task reset"
    3.  Escalate: "I recommend a 10-min low-sensory reset. I’ll stay silent except for a timer."

#### S6 — Shutdown drift (withdrawal / functional drop)
*   **Definition**: Energy down + overload high OR mood low; responsiveness reduces.
*   **Signals (need trend + duration)**:
    *   Long silences, slow responses
    *   Very low motion (freeze) + slumped posture
    *   Monotone speech if speaking
    *   Increased pause ratio
*   **Disconfirmers**: Normal movement + re-engagement
*   **Trigger**: Freeze/low speech + posture collapse for 10–30 min
*   **Interventions**:
    1.  Nudge: "Looks like shutdown drift. Smallest next step?"
    2.  Choice: "Water + sit up / 2-minute reset / message someone safe"
    3.  Escalate: "I can switch to ‘minimal prompts’ and just track recovery for the next hour."

#### S7 — Meltdown risk (escalation + loss of control risk)
*   **Definition**: Arousal very high + overload very high, rapidly worsening.
*   **Signals**:
    *   Rapid pacing/hand movements
    *   Speech becomes fragmented / sharp / louder
    *   Breath dysregulation markers
    *   Repetitive verbalizations (if present)
*   **Disconfirmers**: De-escalation trend (slowing + posture relax)
*   **Trigger**: Arousal + overload above thresholds AND rising quickly over 2–5 min
*   **Interventions**:
    1.  Nudge (short, commanding, not chatty): "Stop. Breathe out. Reduce input now."
    2.  Choice: "Dark/quiet / cold water / leave room for 3 minutes"
    3.  Escalate: "I’m going to be silent for 5 minutes while you regulate. Timer started."
    (For you, "authoritative calm" tends to work better than "therapist gentle." Picard-mode delivery fits here.)

#### S8 — Fatigue / drowsy (daytime)
*   **Definition**: Energy low; safety/decision quality dropping.
*   **Signals**:
    *   Slower speech, more yawns, long blinks
    *   Slumped posture, head nods
    *   Reduced motion + reduced input rate
*   **Disconfirmers**: Brief movement burst + speech clarity returns
*   **Trigger**: Energy markers low for 10–20 min + time-of-day context
*   **Interventions**:
    1.  Nudge: "You look drowsy. Stand + water."
    2.  Choice: "5-min walk / bright light / 20-min rest"
    3.  Escalate: "Avoid high-stakes decisions for 60 minutes; I can schedule a check-in."

#### S9 — Low mood / depressive drift
*   **Definition**: Mood valence low + energy low; withdrawal / negative self-talk risk.
*   **Signals**:
    *   Flat prosody, reduced expressiveness
    *   Long inactivity blocks
    *   Negative content in speech/text (if you ingest it)
*   **Disconfirmers**: Mood improves after basic needs met / movement
*   **Trigger**: Mood low trend over hours/days (not minutes)
*   **Interventions**:
    1.  Nudge: "Minimum viable action?"
    2.  Choice: "Shower / outside 5 min / small tidy"
    3.  Escalate (only if you opt in): "Want a 2-minute ‘reframe’ or just logistics?"

#### S10 — Acute distress event (panic-like / breath discomfort pattern)
*   **Definition**: Sudden spike in arousal with breathing discomfort cues.
*   **Signals**:
    *   Rapid breath + audible gasps/sigh spikes
    *   Speech: "can’t breathe / choking / heart" phrases (if transcribed)
    *   Sudden motion change (stand up abruptly, clutching)
*   **Disconfirmers**: Quick return to baseline after brief startle
*   **Trigger**: Acute change + strong respiratory/voice markers
*   **Interventions**:
    1.  Nudge: "Feet on floor. Long exhale. Name 5 things you see."
    2.  Choice: "Breathing timer / cold water / sit upright"
    3.  Escalate: Ask quick triage questions ("Are you safe? chest pain? fainting?") and prompt human help if severe.

#### S11 — Pain/discomfort suspected (headache, GI, muscle tension)
*   **Definition**: Persistent tension + behavior changes suggesting discomfort.
*   **Signals**:
    *   Face grimace patterns, rubbing temples/neck
    *   Reduced tolerance, irritability
    *   More breaks, less output
*   **Disconfirmers**: Stress-only profile without pain behaviors
*   **Trigger**: Recurrent discomfort gestures + productivity drop + mood shift
*   **Interventions**:
    1.  Nudge: "Body check: neck/jaw/eyes?"
    2.  Choice: "Hydrate / stretch / reduce screen brightness"
    3.  Escalate: suggest logging "pain 1–10" + what changed; propose a recovery block.

#### S12 — Reflux-like throat discomfort pattern
*   **Definition**: Clusters of throat clearing/cough after lying down or late eating (pattern-level).
*   **Signals**:
    *   Throat clear clusters + cough + "swallow" sounds
    *   Occurs late night / after meals (if self-reported)
*   **Disconfirmers**: Random sporadic cough without clustering
*   **Trigger**: Clustered events + timing context
*   **Interventions**:
    1.  Nudge: "Sit more upright + sip water."
    2.  Choice: "Short walk / avoid lying flat / quiet breathing"
    3.  Escalate: log pattern and prompt you to review weekly.

---

### Intervention library (standardized "cards")
To keep the system consistent, every intervention should be one of these "cards" with a cooldown and a success metric.

**Card types**
1.  **Physiology**: long-exhale breathing, cold water, posture reset
2.  **Sensory**: dim lights, headphones, quiet mode, temperature adjust
3.  **Cognitive**: next-action, task slicing, write a 1-sentence bookmark
4.  **Environment**: change rooms, step outside, reduce notifications
5.  **Social**: low-stakes message, schedule check-in
6.  **Recovery**: timer-based rest, nap suggestion, low-stim routine

**Success metrics (loggable)**
*   state score drops (arousal/overload) within 5–15 minutes
*   user marks "helpful"
*   reduced intervention frequency over the next hour

---

### Personalization knobs (tailored to you)
These should be explicit in config/docs because they’ll matter for your brain:

*   **Tone modes**: Picard (authoritative calm), Harvey (direct + tactical), Winston (playful reset)
*   **Prompt density**: low / medium / high
*   **Do Not Disturb windows**: (meetings, late night, "deep work" blocks)
*   **Your top 3 "works every time" resets**: (you define them; system prioritizes)
*   **Trigger watchlist**: doomscroll content, conflict conversations, late caffeine, missed meals
*   **Fail-safe**: "If I reject 2 prompts in 20 minutes, go silent for 45 minutes unless severe escalation."

---

### Implementation notes (so this becomes code cleanly)
*   Compute dimension scores from features with baseline normalization (per time-of-day).
*   Map score regions → states with hysteresis (avoid flipping).
*   Use a policy engine: state + last intervention + cooldown + user preference → next card.
*   Store: features + state + intervention + feedback, not just raw transcripts.
*   Weekly summarizer: "Top triggers / top helpful cards / state trends."
