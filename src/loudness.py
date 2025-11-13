# src/loudness.py
import numpy as np
from scipy.signal import lfilter

# --- idea: apply K-weighting (a standard pre-emphasis) then compute mean square -> LUFS ---
def _k_weighting(x, fs):
    """
    Apply a simplified K-weighting filter (high-pass + high-shelf) used in BS.1770.
    This shapes the audio so loudness matches human perception better than raw RMS.
    """
    # 1) High-pass (~60 Hz). 'a_' coeffs define the filter memory, 'b_' the feed-forward.
    b_hp = np.array([1.0, -2.0, 1.0])
    a_hp = np.array([1.0, -1.9900474548, 0.9900722504])
    y = lfilter(b_hp, a_hp, x)

    # 2) High-shelf (gives more weight to higher freqs)
    b_s = np.array([1.535124859, -2.691696189, 1.198392811])
    a_s = np.array([1.0, -1.690659293, 0.732480774])
    return lfilter(b_s, a_s, y)

def lufs_shortterm(x, fs, eps=1e-12):
    """
    Compute a short-term LUFS-like value for a 2 s window.
    - Input x: mono float32 audio in [-1, 1]
    - We K-weight, then compute mean-square and convert to a LUFS scale.
    Note: This is a close approximation; later we can cross-check vs ffmpeg ebur128.
    """
    y = _k_weighting(x, fs)
    mean_square = np.mean(y**2) + eps
    # The constant (-0.691) is a calibration fudge so numbers line up reasonably with LUFS.
    lufs = -0.691 + 10.0 * np.log10(mean_square)
    return float(lufs)
