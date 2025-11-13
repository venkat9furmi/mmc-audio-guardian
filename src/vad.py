# src/vad.py
import torch
import numpy as np
from silero_vad import load_silero_vad, get_speech_timestamps

class VAD:
    """
    Silero VAD wrapper.
    Expect mono int16 at 16 kHz. We return voiced_ratio in [0,1] for a ~2 s window.
    """
    def __init__(self, fs=16000, threshold=0.5, min_speech_ms=60, min_silence_ms=60):
        self.fs = fs
        self.model = load_silero_vad()
        self.threshold = threshold
        self.min_speech = min_speech_ms
        self.min_silence = min_silence_ms

    def voiced_ratio(self, x_int16):
        # convert int16 → float32 
        wav = torch.from_numpy((x_int16.astype(np.float32) / 32768.0))
        # silero expects shape [T]
        ts = get_speech_timestamps(
            wav, self.model, sampling_rate=self.fs,
            threshold=self.threshold,
            min_speech_duration_ms=self.min_speech,
            min_silence_duration_ms=self.min_silence
        )
        if len(ts) == 0:
            return 0.0
        # compute ratio of speech duration inside this window
        total = len(wav)
        speech = sum(t['end'] - t['start'] for t in ts)
        return float(speech / max(total, 1))
