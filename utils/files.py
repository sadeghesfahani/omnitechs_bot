import json
import os
import subprocess

def get_audio_duration(file_path):
    """Get the duration of an audio file using FFmpeg."""
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/ffmpeg", "-i", file_path, "-f", "null", "-"],
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stderr
        duration_line = [line for line in output.split("\n") if "Duration" in line]
        if duration_line:
            time_str = duration_line[0].split(",")[0].split("Duration:")[1].strip()
            h, m, s = map(float, time_str.replace(":", " ").split())
            return h * 3600 + m * 60 + s  # Convert to seconds
    except Exception as e:
        print(f"Error getting duration: {e}")
    return 0  # Default to 0 if it fails


COST_FILE = "user_costs.json"

def load_costs():
    """Load user costs from a JSON file."""
    if os.path.exists(COST_FILE):
        with open(COST_FILE, "r") as file:
            return json.load(file)
    return {}

def save_costs(user_costs):
    print('here at save cost')
    print(user_costs)
    """Save user costs to a JSON file."""
    with open(COST_FILE, "w", encoding="utf-8") as file:
        json.dump(user_costs, file, indent=4)