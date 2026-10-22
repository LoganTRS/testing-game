"""Best-run score persistence — single-file save/load.

T13: the best-run score (time survived in seconds) is saved to a single
JSON file and loaded on launch. The file path is config-driven
(config.BEST_RUN["file"]).
"""
import json
import os

import config


def _best_run_path():
    """Resolve the best-run file path relative to the project root."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        config.BEST_RUN["file"])


def load_best():
    """Load the best-run score (seconds survived) from the file.

    Returns 0.0 if the file is missing or corrupt.
    """
    path = _best_run_path()
    if not os.path.exists(path):
        return 0.0
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return float(data.get("best_time", 0.0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0.0


def save_best(time_seconds):
    """Save the best-run score (seconds survived) to the file.

    Only overwrites if the new time is greater than the stored best.
    Returns True if the file was written, False if the stored best was
    already higher.
    """
    current_best = load_best()
    if time_seconds <= current_best:
        return False
    path = _best_run_path()
    try:
        with open(path, "w") as f:
            json.dump({"best_time": time_seconds}, f)
        return True
    except OSError:
        return False


def is_new_best(time_seconds):
    """True if `time_seconds` exceeds the stored best (or there is no stored best)."""
    return time_seconds > load_best()
