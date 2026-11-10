import os
import uuid
from typing import BinaryIO, Optional
from app.core.config import settings
from app.core.exceptions import BadRequestError


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.local_dir = os.path.abspath(settings.STORAGE_LOCAL_DIR)
        if self.backend == "local":
            os.makedirs(self.local_dir, exist_ok=True)

    def save_file(self, file_obj: BinaryIO, filename: str, mime_type: str) -> str:
        """Save file and return a unique file key."""
        ext = os.path.splitext(filename)[1].lower()
        unique_key = f"{uuid.uuid4().hex}{ext}"

        if self.backend == "local":
            target_path = os.path.join(self.local_dir, unique_key)
            with open(target_path, "wb") as f:
                f.write(file_obj.read())
            return unique_key
        else:
            # S3 implementation (stub/placeholder for cloud deployment)
            raise NotImplementedError("S3 storage client not configured in dev mode.")

    def get_file_path(self, file_key: str) -> str:
        """Get local absolute path for streaming file."""
        if self.backend == "local":
            safe_key = os.path.basename(file_key)
            path = os.path.join(self.local_dir, safe_key)
            if not os.path.exists(path):
                raise BadRequestError(message_key="resource_not_found")
            return path
        raise NotImplementedError("S3 streaming requires presigned URL or object retrieval.")

    def delete_file(self, file_key: str) -> bool:
        """Remove file from storage."""
        if self.backend == "local":
            safe_key = os.path.basename(file_key)
            path = os.path.join(self.local_dir, safe_key)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    return True
                except Exception:
                    return False
        return False


storage_service = StorageService()

