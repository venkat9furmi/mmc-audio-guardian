# src/step1_analyze_wav.py  (diagnostic version)
import argparse, csv, os
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from vad import VAD
from loudness import lufs_shortterm

def resample_to(x, fs_in, fs_out):
    from math import gcd
    g = gcd(int(fs_in), int(fs_out))
    up = int(fs_out // g)
    down = int(fs_in // g)
    return resample_poly(x, up, down), fs_out

def main(path):
    print(f" Loading: {os.path.abspath(path)}")
    if not os.path.exists(path):
        print(" File does not exist. Check the --path.")
        return

    x, fs = sf.read(path, dtype='float32')
    if x.ndim > 1: x = x.mean(axis=1)
    dur = len(x) / fs
    print(f" Loaded {len(x)} samples @ {fs} Hz (duration ~{dur:.2f}s)")

    x48, fs_lufs = resample_to(x, fs, 48000)
    x16, _       = resample_to(x48, fs_lufs, 16000)
    x16_i16 = (np.clip(x16, -1, 1) * 32767).astype(np.int16)

    win = int(2.0 * fs_lufs)
    hop = int(0.5 * fs_lufs)

    total_iters = max(0, (len(x48) - win) // hop)
    print(f" Window=2.0s  Hop=0.5s  → iterations planned: {total_iters}")
    if total_iters <= 0:
        print(" Audio is too short (<2s). Use a longer sample.")
        return

    vad = VAD(fs=16000, threshold=0.5)
    speech_hist, amb_hist = [], []

    with open('logs.csv','w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["time_s","voiced_ratio","lufs_now","speech_med","ambient_med","snr_est_db"])

        for i in range(0, len(x48)-win, hop):
            t = i / fs_lufs
            seg48 = x48[i:i+win]
            i16 = int(i * 16000 / fs_lufs)
            seg16 = x16_i16[i16:i16 + int(2.0 * 16000)]

            voiced = vad.voiced_ratio(seg16)
            lufs_now = lufs_shortterm(seg48, fs_lufs)

            speech_med = ambient_med = None
            if voiced > 0.6: speech_hist.append(lufs_now)
            if voiced < 0.1: amb_hist.append(lufs_now)
            if speech_hist:  speech_med  = float(np.median(speech_hist[-10:]))
            if amb_hist:     ambient_med = float(np.median(amb_hist[-10:]))

            snr = (speech_med - ambient_med) if (speech_med is not None and ambient_med is not None) else None
            w.writerow([
                f"{t:.2f}", f"{voiced:.2f}", f"{lufs_now:.2f}",
                "" if speech_med is None else f"{speech_med:.2f}",
                "" if ambient_med is None else f"{ambient_med:.2f}",
                "" if snr is None else f"{snr:.2f}"
            ])

            msg = f"[t={t:6.2f}s] voiced={voiced:0.2f} | LUFS_now={lufs_now:6.2f}"
            if speech_med is not None:  msg += f" | speech_med={speech_med:6.2f}"
            if ambient_med is not None: msg += f" | amb_med={ambient_med:6.2f}"
            if snr is not None:         msg += f" | SNR={snr:5.2f} dB"
            print(msg)

    print(" Done. Wrote logs.csv.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True)
    args = p.parse_args()
    main(args.path)
