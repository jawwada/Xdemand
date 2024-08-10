import os
import pickle
import hashlib
def disk_cache_dataframe(func):
    def wrapper(*args, **kwargs):
        # Create a unique key based on the function name and arguments
        key = hashlib.sha256((func.__name__ + str(args) + str(kwargs)).encode()).hexdigest()
        cache_file = f'cache-dataframes/{key}.pkl'

        # Check if the result is already cached
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # Compute the result and cache it
        result = func(*args, **kwargs)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

        return result

    return wrapper