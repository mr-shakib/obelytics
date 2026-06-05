from arq.connections import RedisSettings
from app.core.config import settings

redis_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    database=1,  # separate Redis DB from cache (DB 0)
)


class WorkerSettings:
    redis_settings = redis_settings
    functions: list = []  # tasks registered here as phases are built
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # retain job results for 1 hour
    retry_jobs = True
    max_tries = 3
