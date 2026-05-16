from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError

from shared.config import settings


async def enforce_rate_limit(redis: Redis, tenant_id: str) -> None:
    key = f"nexus:rl:{tenant_id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.rate_limit_window_seconds)
        if count > settings.rate_limit_max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except RedisError:
        # Fail-open in dev if Redis is unavailable.
        return

