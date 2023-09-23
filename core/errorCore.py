import functools
import traceback

class CustomeError(Exception):
    def __init__(self, message):
        self.message = message

def handle_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return False, func(*args, **kwargs)
        except CustomeError as e:
            return True, e.message
        except Exception:
            traceback.print_exc()
            return True, traceback.format_exc()
            # return True, str(f"Error: {e}")
    return wrapper