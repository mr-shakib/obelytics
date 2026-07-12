from arq.connections import RedisSettings
from app.core.config import settings
from app.workers.tasks.reports import generate_report_run

redis_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    database=1,  # separate Redis DB from cache (DB 0)
)


class WorkerSettings:
    redis_settings = redis_settings
    functions: list = [generate_report_run]
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # retain job results for 1 hour
    retry_jobs = True
    max_tries = 3
