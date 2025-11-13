# src/decision.py
import time

class DecisionEngine:
    """
    Emits alerts on state changes (audible, loudness, balance).
    Uses cooldown to avoid spam and 1 dB hysteresis to prevent flapping.
    """

    def __init__(self, cfg):
        t = cfg['targets']; a = cfg['alerts']
        self.speech_min = t['speech_lufs_min']
        self.speech_max = t['speech_lufs_max']
        self.snr_min    = t['snr_min']
        self.snr_max    = t['snr_max']
        self.cooldown   = a['cooldown_sec']
        self.hyst       = 1.0  # dB
        self.last_sent  = {}

        # remembered states
        self.prev_audible = None              # True/False
        self.prev_loudness_state = "unknown"  # quiet/ok/loud/unknown
        self.prev_balance_state  = "unknown"  # under/ok/over/unknown
        self.miss_cnt = 0  # for not-audible debounce (~2 s)

        print(f"DecisionEngine v2 (state-change) loaded; cooldown={self.cooldown}s")

    def _ready(self, key):
        now = time.time()
        if key not in self.last_sent or (now - self.last_sent[key]) > self.cooldown:
            self.last_sent[key] = now
            return True
        return False

    def _classify_loudness(self, speech_med):
        if speech_med is None:
            return "unknown"
        if speech_med < (self.speech_min - self.hyst):
            return "quiet"
        if speech_med > (self.speech_max + self.hyst):
            return "loud"
        return "ok"

    def _classify_balance(self, snr):
        if snr is None:
            return "unknown"
        if snr < (self.snr_min - self.hyst):
            return "under"
        if snr > (self.snr_max + self.hyst):
            return "over"
        return "ok"

    def evaluate(self, lufs_now, speech_med, ambient_med, snr, audible_flag):
        events = []

        # ----- Audible / Not audible (with debounce) -----
        if not audible_flag:
            self.miss_cnt += 1
        else:
            self.miss_cnt = 0
        audible_state = (self.miss_cnt < 4)  # false after ~2 s below -50 LUFS

        if self.prev_audible is None:
            self.prev_audible = audible_state
        elif audible_state != self.prev_audible and self._ready("audible_change"):
            if audible_state:
                events.append(("Audio restored", "Level back above −50 LUFS", "info"))
            else:
                events.append(("Audio not audible", "Level below −50 LUFS for ~2 s", "error"))
            self.prev_audible = audible_state

        if not audible_state:
            return events  # when silent, skip other checks

        # ----- Loudness state (quiet/ok/loud) -----
        loud_state = self._classify_loudness(speech_med)
        if loud_state != self.prev_loudness_state and self._ready(f"loud_{loud_state}"):
            if loud_state == "quiet":
                events.append(("Too quiet", f"Speech {speech_med:.1f} LUFS (target −20 ±3)", "warn"))
            elif loud_state == "loud":
                events.append(("Too loud", f"Speech {speech_med:.1f} LUFS (target −20 ±3)", "warn"))
            elif loud_state == "ok" and self.prev_loudness_state in ("quiet","loud"):
                events.append(("Loudness OK", f"Speech {speech_med:.1f} LUFS within range", "info"))
            self.prev_loudness_state = loud_state

        # ----- Balance state (under/ok/over) -----
        bal_state = self._classify_balance(snr)
        if bal_state != self.prev_balance_state and self._ready(f"bal_{bal_state}"):
            if bal_state == "under":
                events.append(("Voice under crowd", f"SNR {snr:.1f} dB (target {self.snr_min}–{self.snr_max})", "warn"))
            elif bal_state == "over":
                events.append(("Voice dominates crowd", f"SNR {snr:.1f} dB (target {self.snr_min}–{self.snr_max})", "warn"))
            elif bal_state == "ok" and self.prev_balance_state in ("under","over"):
                events.append(("Balance OK", f"SNR {snr:.1f} dB within target", "info"))
            self.prev_balance_state = bal_state

        return events
