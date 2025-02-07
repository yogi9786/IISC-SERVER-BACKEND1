import os
import base64

# Generate a random 32-byte key and encode it in base64
secret_key = base64.b64encode(os.urandom(32)).decode('utf-8')
print(secret_key)
