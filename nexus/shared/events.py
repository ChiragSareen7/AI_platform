import json
from redis.asyncio import Redis


async def publish_event(redis: Redis, channel: str, payload: dict) -> None:
    await redis.publish(channel, json.dumps(payload))

