from arq import func
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks.integrity import run_integrity_job
from app.workers.tasks.reports import generate_report_run

redis_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    database=1,  # separate Redis DB from cache (DB 0)
)


class WorkerSettings:
    redis_settings = redis_settings
    functions: list = [
        generate_report_run,
        # Reading a paper or auditing a whole exam on a model can take many minutes.
        # Not retried (the job records its own failure) and no result kept.
        func(
            run_integrity_job,
            timeout=settings.INTEGRITY_JOB_TIMEOUT_SECONDS,
            keep_result=0,
            max_tries=1,
        ),
    ]
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # retain job results for 1 hour
    retry_jobs = True
    max_tries = 3
