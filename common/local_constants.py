from joblib import Memory
local_cache_directory = "cache_directory"
memory = Memory(local_cache_directory, verbose=0)
memory.timeout = 60*60*24*7

region_warehouse_codes = {
    'USA': 'US',
    'US': 'US',
    'UK': 'UK',
    'CA': 'CA',
    'IT': 'DE',
    'DE': 'DE',
    'FR': 'DE',
    'ES': 'DE',
    'AU': 'DE'
}
