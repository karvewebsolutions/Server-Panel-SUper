from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DNSProvider(ABC):
    name: str

    @abstractmethod
    def create_record(self, zone: str, record: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete_record(self, zone: str, record_id: str) -> None:
        ...

    @abstractmethod
    def list_records(self, zone: str) -> List[Dict[str, Any]]:
        ...
