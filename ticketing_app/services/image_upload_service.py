

from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.cloudinary import CloudinaryClient
from core.file_hash import ComputeFileHash
from fastapi import HTTPException
from repositories.event_repo import EventRepo
from repositories.venue_repo import VenueRepo

MAX_DAILY_UPLOADS = 3


class UploadImageService:
    def __init__(self, db):
        self.event_repo:EventRepo=EventRepo(db)
        self.venue_repo: VenueRepo = VenueRepo(db)
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.compute: ComputeFileHash = ComputeFileHash()

    def _enforce_daily_quota(self, user_id: int, incoming_count: int):
        today_start = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tomorrow = today_start + timedelta(days=1)

        count = self.venue_repo.count_user_uploads_between(
            user_id=user_id,
            start=today_start,
            end=tomorrow,
        )

        if count >= MAX_DAILY_UPLOADS:
            raise HTTPException(
                status_code=429, detail="Daily upload limit reached")

    def sync_upload_venue_image(self, user_id: int, venue_id: int, file_path: str):
     try:

        self._enforce_daily_quota(user_id=user_id, incoming_count=1)
        path = Path(file_path)

        if not path.exists():
            raise HTTPException(status_code=400, detail="File not found")

    
        if path.stat().st_size > 50 * 1024 * 1024:
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="File too large")

        suffix = path.suffix.lower()
        video_extensions = {".mp4", ".mov", ".webm", ".mkv"}

        resource_type = "video" if suffix in video_extensions else "image"

        image_hash = self.compute.compute_file_hash_sync(image_url=file_path)
        existing = self.venue_repo.sync_get_by_hash(
            image_hash=image_hash,
            venue_id=venue_id
        )
        if existing:
            path.unlink(missing_ok=True)
            raise HTTPException(400, "This image has already been uploaded")
        result = self.cloudinary.backend_upload(
            resource_type=resource_type, folder="venue_uploads", file_path=file_path)
        image_url = result.get("secure_url")
        public_id = result.get("public_id")
        path.unlink(missing_ok=True)

        self.venue_repo.sync_upload_venue_image(
            user_id=user_id,
            venue_id=venue_id,
            image_hash=image_hash,
            image_url=image_url,
            public_id=public_id
        )
        return {
            "image_url": image_url,

        }
     except Exception as e:
            self.cloudinary.sync_delete(public_id=public_id, resource_type=resource_type)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    def sync_upload_venue_images(
        self,
        user_id: int,
        venue_id: int,
        file_paths: list[str],
    ):
        if not file_paths:
            raise HTTPException(status_code=400, detail="No files provided")

        if len(file_paths) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum of 3 files allowed per request",
            )

   
        self._enforce_daily_quota(user_id=user_id, incoming_count=len(file_paths))

        uploaded_results = []
        uploaded_cloudinary_ids = []

        try:
            for file_path in file_paths:
                path = Path(file_path)

                if not path.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"File not found: {file_path}",
                    )

                
                if path.stat().st_size > 50 * 1024 * 1024:
                    path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {file_path}",
                    )

                suffix = path.suffix.lower()
                video_extensions = {".mp4", ".mov", ".webm", ".mkv"}

                resource_type = (
                    "video" if suffix in video_extensions else "image"
                )

                
                image_hash = self.compute.compute_file_hash_sync(
                    image_url=str(path)
                )

                existing = self.venue_repo.sync_get_by_hash(
                    image_hash=image_hash,
                    venue_id=venue_id,
                )

                if existing:
                    path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Duplicate file detected: {file_path}",
                    )

               
                result = self.cloudinary.backend_upload(
                    resource_type=resource_type,
                    folder="venue_uploads",
                    file_path=str(path),
                )

                image_url = result.get("secure_url")
                public_id = result.get("public_id")

                uploaded_cloudinary_ids.append(
                    (public_id, resource_type)
                )

               
                self.venue_repo.sync_upload_venue_image(
                    user_id=user_id,
                    venue_id=venue_id,
                    image_hash=image_hash,
                    image_url=image_url,
                    public_id=public_id,
                )

                uploaded_results.append(
                    {
                        "image_url": image_url,
                        
                    }
                )

                path.unlink(missing_ok=True)

            return {
                "uploaded": uploaded_results,
            }

        except Exception as e:
            
            for public_id, resource_type in uploaded_cloudinary_ids:
                try:
                    self.cloudinary.sync_delete(
                        public_id=public_id,
                        resource_type=resource_type,
                    )
                except Exception:
                    pass

            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}",
            )
    def sync_upload_event_images(
        self,
        user_id: int,
        event_id: int,
        file_paths: list[str],
    ):
        if not file_paths:
            raise HTTPException(status_code=400, detail="No files provided")

        if len(file_paths) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum of 3 files allowed per request",
            )

   
        self._enforce_daily_quota(user_id=user_id, incoming_count=len(file_paths))

        uploaded_results = []
        uploaded_cloudinary_ids = []

        try:
            for file_path in file_paths:
                path = Path(file_path)

                if not path.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"File not found: {file_path}",
                    )

                
                if path.stat().st_size > 50 * 1024 * 1024:
                    path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {file_path}",
                    )

                suffix = path.suffix.lower()
                video_extensions = {".mp4", ".mov", ".webm", ".mkv"}

                resource_type = (
                    "video" if suffix in video_extensions else "image"
                )

                
                image_hash = self.compute.compute_file_hash_sync(
                    image_url=str(path)
                )

                existing = self.event_repo.sync_get_by_hash(
                    image_hash=image_hash,
                    event_id=event_id,
                )

                if existing:
                    path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Duplicate file detected: {file_path}",
                    )

               
                result = self.cloudinary.backend_upload(
                    resource_type=resource_type,
                    folder="venue_uploads",
                    file_path=str(path),
                )

                image_url = result.get("secure_url")
                public_id = result.get("public_id")

                uploaded_cloudinary_ids.append(
                    (public_id, resource_type)
                )

               
                self.event_repo.sync_upload_event_image(
                    user_id=user_id,
                    event_id=event_id,
                    image_hash=image_hash,
                    image_url=image_url,
                    public_id=public_id,
                )

                uploaded_results.append(
                    {
                        "image_url": image_url,
                        
                    }
                )

                path.unlink(missing_ok=True)

            return {
                "uploaded": uploaded_results,
            }

        except Exception as e:
            
            for public_id, resource_type in uploaded_cloudinary_ids:
                try:
                    self.cloudinary.sync_delete(
                        public_id=public_id,
                        resource_type=resource_type,
                    )
                except Exception:
                    pass

            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}",
            )
