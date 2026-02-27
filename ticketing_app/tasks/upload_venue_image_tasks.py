
import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from services.image_upload_service import UploadImageService


@shared_task(
    name="sync_upload_venue_images",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def upload_image_tasks(user_id: str, venue_id:int, file_path:str):
    try:
        user_int =int(user_id)
        venue_int=int(venue_id)
        if not user_int:
            return ValueError("Invalid User ID")
        updated = upload_image(user_id=user_int, file_path=file_path, venue_id=venue_int)
       
        

        return updated
    except Exception:
        raise


def upload_image(user_id:int, file_path:str, venue_id:int):
    db = SyncSessionLocal()
   
    try:
        return UploadImageService(db).sync_upload_venue_image(user_id=user_id, file_path=file_path, venue_id=venue_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close_all()
@shared_task(
    name="sync_upload_venue_images",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def upload_images_tasks(user_id: str, venue_id: str, file_paths: list[str]):
    try:
        user_int = int(user_id)
        venue_int = int(venue_id)

        if not user_int:
            raise ValueError("Invalid User ID")

        updated = upload_images(
            user_id=user_int,
            venue_id=venue_int,
            file_paths=file_paths,  
        )

        

        return updated

    except Exception:
        raise


def upload_images(user_id: int, venue_id: int, file_paths: list[str]):
    db = SyncSessionLocal()

    try:
        return UploadImageService(db).sync_upload_venue_images(
            user_id=user_id,
            venue_id=venue_id,
            file_paths=file_paths,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()