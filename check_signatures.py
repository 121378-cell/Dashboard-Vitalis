from garminconnect import Garmin
import inspect

try:
    sig = inspect.signature(Garmin.get_training_status)
    print(f"get_training_status: {sig}")
except Exception as e:
    print(f"get_training_status: Error {e}")

try:
    sig = inspect.signature(Garmin.get_stats)
    print(f"get_stats: {sig}")
except Exception as e:
    print(f"get_stats: Error {e}")
