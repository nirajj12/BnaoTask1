from fastapi import UploadFile

class IngestionFile:
    """
    Safe file container for background ingestion.
    """
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getbuffer(self) -> bytes:
        return self._data
