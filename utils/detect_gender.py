import librosa
import numpy as np


def detect_gender_with_pitch(wav_path, pitch_threshold=160):
    """
    Returns 'male' or 'female' based on the average fundamental frequency (pitch)
    of the audio in wav_path. The pitch_threshold parameter (in Hz) determines the cutoff.

    Note:
      - Typical male voices have an average F0 around 85-180 Hz, while female voices are generally higher.
      - This method can be less robust in noisy conditions or for recordings without clear speech.
    """
    try:
        # Load audio file (preserving original sample rate)
        y, sr = librosa.load(wav_path, sr=None)

        # Extract the fundamental frequency (F0) using librosa's pyin function.
        # fmin and fmax define the expected pitch range (adjust as necessary).
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7')
        )

        # Remove unvoiced frames (where f0 is NaN)
        f0_clean = f0[~np.isnan(f0)]
        if len(f0_clean) == 0:
            return "unknown"

        avg_f0 = np.mean(f0_clean)

        # Compare average pitch to the threshold
        return "male" if avg_f0 < pitch_threshold else "female"
    except Exception as e:
        print(f"Error detecting gender with pitch: {e}")
        return "unknown"
