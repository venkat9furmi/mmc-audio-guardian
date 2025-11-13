# src/step2_run_wav.py
import argparse, csv, yaml, numpy as np, soundfile as sf
from scipy.signal import resample_poly
from vad import VAD
from loudness import lufs_shortterm
from decision import DecisionEngine
from alerts import send_console, send_teams

def resample_to(x, fs_in, fs_out):
    from math import gcd
    g = gcd(int(fs_in), int(fs_out))
    up = int(fs_out // g)
    down = int(fs_in // g)
    return resample_poly(x, up, down), fs_out

def main(path, config_path):
    cfg = yaml.safe_load(open(config_path, 'r'))
    feed = cfg.get("feed_name", "Feed")

    x, fs = sf.read(path, dtype='float32')
    if x.ndim > 1:
        x = x.mean(axis=1)

    # Resample for LUFS and VAD
    x48, _ = resample_to(x, fs, 48000)
    x16, _ = resample_to(x48, 48000, 16000)
    x16_i16 = (np.clip(x16, -1, 1) * 32767).astype(np.int16)

    win = int(2.0 * 48000)
    hop = int(0.5 * 48000)

    vad = VAD(fs=16000, threshold=0.5)
    decider = DecisionEngine(cfg)

    speech_hist, amb_hist = [], []

    with open('logs_step2.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["time_s", "voiced", "lufs_now", "speech_med",
                    "ambient_med", "snr_est_db", "audible"])

        for i in range(0, len(x48) - win, hop):
            t = i / 48000
            seg48 = x48[i:i+win]
            i16 = int(i * 16000 / 48000)
            seg16 = x16_i16[i16:i16 + int(2.0 * 16000)]

            voiced = vad.voiced_ratio(seg16)
            lufs_now = lufs_shortterm(seg48, 48000)
            audible = (lufs_now > -50)

            speech_med = ambient_med = None
            if voiced > 0.6:
                speech_hist.append(lufs_now)
            if voiced < 0.1:
                amb_hist.append(lufs_now)
            if speech_hist:
                speech_med = float(np.median(speech_hist[-10:]))
            if amb_hist:
                ambient_med = float(np.median(amb_hist[-10:]))

            snr = (speech_med - ambient_med) if (speech_med and ambient_med) else None

            # --- Evaluate decisions ---
            events = decider.evaluate(lufs_now, speech_med, ambient_med, snr, audible)
            for title, text, sev in events:
                send_console(feed, title, text, sev)
                send_teams(cfg['alerts'].get('teams_webhook', ''), feed, title, text, sev)

            w.writerow([f"{t:.2f}", f"{voiced:.2f}", f"{lufs_now:.2f}",
                        "" if speech_med is None else f"{speech_med:.2f}",
                        "" if ambient_med is None else f"{ambient_med:.2f}",
                        "" if snr is None else f"{snr:.2f}", int(audible)])

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    main(args.path, args.config)
