import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from services.image_upload_service import UploadImageService


@shared_task(
    name="sync_upload_event_images",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def upload_images_tasks(user_id: str, event_id: str, file_paths: list[str]):
    try:
        user_int = int(user_id)
        event_int = int(event_id)

        if not user_int:
            raise ValueError("Invalid User ID")

        updated = upload_images(
            user_id=user_int,
            event_id=event_int,
            file_paths=file_paths,
        )

        return updated

    except Exception:
        raise


def upload_images(user_id: int, event_id: int, file_paths: list[str]):
    db = SyncSessionLocal()

    try:
        return UploadImageService(db).sync_upload_event_images(
            user_id=user_id,
            event_id=event_id,
            file_paths=file_paths,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
