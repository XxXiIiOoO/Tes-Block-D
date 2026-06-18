import time

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


#Eto otdelnyy shag get_redis_connection, chtoby ne kopipastit odno i to zhe.
def get_redis_connection() -> Redis:
    return Redis.from_url(settings.redis_url)


#Funkciya wait_for_redis zakryvaet konkretnuyu zadachu v etom meste.
def wait_for_redis(max_attempts: int = 15, delay_seconds: int = 2) -> Redis:
    connection = get_redis_connection()
    for attempt in range(max_attempts):
        try:
            connection.ping()
            return connection
        except RedisError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay_seconds)

    return connection
