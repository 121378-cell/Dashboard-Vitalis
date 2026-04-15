from garminconnect import Garmin
import inspect

methods = [m for m, _ in inspect.getmembers(Garmin, predicate=inspect.isfunction)]
print('\n'.join(methods))
