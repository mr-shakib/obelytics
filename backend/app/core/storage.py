import io
import posixpath

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY or None,
    api_secret=settings.CLOUDINARY_API_SECRET or None,
    secure=True,
)

# Folders whose objects are non-image files (PDFs, docs) delivered byte-for-byte,
# as opposed to logos which Cloudinary manages as "image" resources.
_RAW_FOLDERS = {"reports", "accreditation"}


def _resource_type(bucket: str) -> str:
    return "raw" if bucket in _RAW_FOLDERS else "image"


def _public_id(bucket: str, key: str) -> str:
    if _resource_type(bucket) == "raw":
        return f"{bucket}/{key}"
    stem, _ext = posixpath.splitext(key)
    return f"{bucket}/{stem}"


async def ensure_bucket(bucket: str) -> None:
    # No-op: Cloudinary has no bucket-provisioning step, folders are implicit.
    return


async def put_object(bucket: str, key: str, body: bytes, content_type: str) -> None:
    resource_type = _resource_type(bucket)
    public_id = _public_id(bucket, key)
    await run_in_threadpool(
        cloudinary.uploader.unsigned_upload,
        io.BytesIO(body),
        settings.CLOUDINARY_UPLOAD_PRESET,
        public_id=public_id,
        resource_type=resource_type,
    )


async def presigned_get_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    resource_type = _resource_type(bucket)
    public_id = _public_id(bucket, key)
    url, _options = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=resource_type,
        secure=True,
    )
    return url


async def delete_object(bucket: str, key: str) -> None:
    resource_type = _resource_type(bucket)
    public_id = _public_id(bucket, key)
    await run_in_threadpool(
        cloudinary.uploader.destroy,
        public_id,
        resource_type=resource_type,
    )
