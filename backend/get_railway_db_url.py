#!/usr/bin/env python3
"""Helper script to get DATABASE_URL from Railway environment."""
import os
import sys

db_url = os.getenv('DATABASE_URL', '')
if db_url:
    print(db_url)
    sys.exit(0)
else:
    print("DATABASE_URL not found", file=sys.stderr)
    sys.exit(1)



