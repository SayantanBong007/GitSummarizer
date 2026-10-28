"""Shared rate limiter instance.

Lives in its own module (not backend/main.py) so route modules can import and
apply @limiter.limit(...) without a circular import -- main.py imports the
routers, so the routers can't import back from main.py.

No auth exists on this API. Rate limiting, keyed by client IP, is the one real
guard against a single client cloning/analyzing repos in a loop and running up
LLM cost or exhausting worker capacity. Requires uvicorn's --proxy-headers (set
in docker-compose.yml) to see the real client address through nginx instead of
nginx's own container IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
