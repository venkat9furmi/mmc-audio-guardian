# src/batch_analyze.py
# Batch version of step1_analyze_wav.py
# It loops through all .wav files and saves logs to ./logs/

import os, csv, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.append(os.path.dirname(__file__))
from vad import VAD
from loudness import lufs_shortterm

def resample_to(x, fs_in, fs_out):
    from math import gcd
    g = gcd(int(fs_in), int(fs_out))
    up = int(fs_out // g)
    down = int(fs_in // g)
    return resample_poly(x, up, down), fs_out

def analyze_one(path, out_csv):
    x, fs = sf.read(path, dtype='float32')
    if x.ndim > 1:
        x = x.mean(axis=1)
    dur = len(x) / fs
    if dur < 2:
        print(f"⚠️  Skipping (too short <2s): {path}")
        return

    x48, fs_lufs = resample_to(x, fs, 48000)
    x16, _       = resample_to(x48, fs_lufs, 16000)
    x16_i16 = (np.clip(x16, -1, 1) * 32767).astype(np.int16)

    win = int(2.0 * fs_lufs)
    hop = int(0.5 * fs_lufs)

    vad = VAD(fs=16000, threshold=0.5)
    speech_hist, amb_hist = [], []

    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["time_s","voiced_ratio","lufs_now","speech_med","ambient_med","snr_est_db"])

        for i in range(0, len(x48) - win, hop):
            t = i / fs_lufs
            seg48 = x48[i:i+win]
            i16 = int(i * 16000 / fs_lufs)
            seg16 = x16_i16[i16:i16 + int(2.0 * 16000)]

            voiced = vad.voiced_ratio(seg16)
            lufs_now = lufs_shortterm(seg48, fs_lufs)

            speech_med = ambient_med = None
            if voiced > 0.6:
                speech_hist.append(lufs_now)
            if voiced < 0.1:
                amb_hist.append(lufs_now)
            if speech_hist:
                speech_med = float(np.median(speech_hist[-10:]))
            if amb_hist:
                ambient_med = float(np.median(amb_hist[-10:]))

            snr = (speech_med - ambient_med) if (speech_med is not None and ambient_med is not None) else None

            w.writerow([
                f"{t:.2f}", f"{voiced:.2f}", f"{lufs_now:.2f}",
                "" if speech_med is None else f"{speech_med:.2f}",
                "" if ambient_med is None else f"{ambient_med:.2f}",
                "" if snr is None else f"{snr:.2f}"
            ])
    print(f" analyzed {os.path.basename(path)} → {out_csv}")

def main():
    in_dir = os.path.join("data", "samples", "wav")
    out_dir = "logs"
    os.makedirs(out_dir, exist_ok=True)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(".wav")]
    if not files:
        print(" No .wav files found.")
        return

    for f in files:
        src = os.path.join(in_dir, f)
        dst = os.path.join(out_dir, f"log_{os.path.splitext(f)[0]}.csv")
        analyze_one(src, dst)

if __name__ == "__main__":
    main()
