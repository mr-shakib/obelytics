from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from app.core.config import settings


@asynccontextmanager
async def _client() -> AsyncIterator:
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    ) as client:
        yield client


async def ensure_bucket(bucket: str) -> None:
    async with _client() as client:
        try:
            await client.head_bucket(Bucket=bucket)
        except ClientError:
            await client.create_bucket(Bucket=bucket)


async def put_object(bucket: str, key: str, body: bytes, content_type: str) -> None:
    await ensure_bucket(bucket)
    async with _client() as client:
        await client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


async def presigned_get_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    async with _client() as client:
        return await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )


async def delete_object(bucket: str, key: str) -> None:
    async with _client() as client:
        await client.delete_object(Bucket=bucket, Key=key)
