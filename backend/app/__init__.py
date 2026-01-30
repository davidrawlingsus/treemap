# Backend application package

# Debug: Print environment variable status at import time
import os
print("=" * 50)
print("[APP INIT] Environment variable check at Python import:")
print(f"[APP INIT] DATABASE_URL present: {'YES' if os.environ.get('DATABASE_URL') else 'NO'}")
print(f"[APP INIT] BLOB_READ_WRITE_TOKEN present: {'YES' if os.environ.get('BLOB_READ_WRITE_TOKEN') else 'NO'}")
print(f"[APP INIT] Total env vars: {len(os.environ)}")
print(f"[APP INIT] Env vars containing 'DATABASE': {[k for k in os.environ.keys() if 'DATABASE' in k.upper()]}")
print(f"[APP INIT] Env vars containing 'BLOB': {[k for k in os.environ.keys() if 'BLOB' in k.upper()]}")
print("=" * 50)
