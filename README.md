# mmc-audio-guardian  
_AI-based audio monitoring used  for live sports commentary (prototype for mmc sport)

# 1. Overview

Live football commentary is produced in up to 11 languages in parallel.  
Today, manually check each audio feed.

Is the livestream actually audible?
Is the commentator too loud or too quiet?
Is the balance between commentator and stadium sound okay?

this is a small prototype that automates these checks.

It listens to an audio feed, measures loudness and voice/background balance, and raises alerts like:

- `Too quiet – Speech -35.9 LUFS (target −20 ±3)`
- `Voice dominates crowd – SNR 20.4 dB (target 4–14)`
- `Audio not audible – Level below −50 LUFS for ~2 s`

Alerts are printed in the console and sent to a webhook (Teams-compatible JSON).  
For this prototype, the webhook was tested using Pipedream.

---

## 2. Features

 Detects if commentary is audible or accidentally silent
 Measures speech loudness in LUFS (broadcast standard)
 Estimates **SNR** between commentator and crowd noise
 Classifies states: OK, Too quiet, Too loud, Voice under crowd, Voice dominates crowd, Not audible
 Sends alerts to a webhook.
 Uses a simple rule-based decision engine on top of AI features.

Under the hood:

 Silero-VAD (AI model) for speech detection
 Python DSP for LUFS and SNR
 A small state machine to avoid spamming alerts

---

## 3. Architecture

The prototype is structured in four logical layers:

1. Input Layer 
    Source: WAV files  simulating live commentary feeds.  
    In a production setup, this could be an ffmpeg pipeline .

2. Analysis Layer (src/vad.py, src/loudness.py, src/step1_analyze_wav.py)  
   - Silero VAD → speech probability (voiced_ratio) per 2 s window  
   - LUFS short-term loudness → lufs_now  
   - Separation of speech vs ambient segments → rolling medians  
   - SNR estimation: speech_med - ambient_med

3. Decision Layer (`src/decision.py`)  
   - Rule-based engine with thresholds from `config.yaml`:
     - Speech loudness range (e.g. −23 to −17 LUFS)
     - SNR range (e.g. 4 to 14 dB) 
   - Tracks states over time:
     - Audible / Not audible  
     - Loudness: quiet, ok, loud  
     - Balance: under, ok, over
   - Emits alerts only on state changes (e.g. `ok → quiet`, `over → ok`) with a configurable cooldown.

4. Communication Layer (src/alerts.py)  
   - Prints alerts to the console  
   - Sends JSON payloads to a webhook URL.

---

## 4. Setup

 4.1. Clone and create virtual environment


git clone https://github.com/<your-username>/mmc-audio-guardian.git

