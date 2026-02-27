import asyncio
import hashlib


import requests
from fastapi import HTTPException


class ComputeFileHash:

    def compute_file_hash_sync(self, file_url: str) -> str:
        try:
            resp = requests.get(file_url, timeout=30)
        except requests.RequestException:
            raise HTTPException(status_code=400, detail="Failed to fetch file")

        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch file")

        return hashlib.sha256(resp.content).hexdigest()
