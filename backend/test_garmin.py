import time  
import sys  
sys.path.insert(0, '.')  
from app.utils.garmin import get_garmin_client, _parse_retry_after, _is_rate_limit_error  
msg1 = 'Too Many Requests: retry after 3600 seconds'  
msg2 = 'Rate limit exceeded. Retry-After: 1800'  
msg3 = 'Please try again in 300 seconds'  
r1 = _parse_retry_after(msg1)  
r2 = _parse_retry_after(msg2)  
r3 = _parse_retry_after(msg3)  
print(f'Test retry-after: {r1}s, {r2}s, {r3}s')  
print(f'Rate limit detection 429: {_is_rate_limit_error("Error 429")}')  
print(f'Rate limit detection 500: {_is_rate_limit_error("Error 500")}')  
print('SUCCESS') 
