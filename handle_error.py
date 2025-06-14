import functools


def catch_errors(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"Unexpected error in {func.__name__}: {e}")
    return wrapper
