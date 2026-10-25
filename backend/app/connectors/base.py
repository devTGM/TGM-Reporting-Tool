from abc import ABC, abstractmethod
from typing import List, Dict, Any
from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile

class BaseAdConnector(ABC):
    """
    Abstract Base Connector for Ad Platforms.
    Each platform connector extracts raw insights and maps them to UnifiedAdRecord objects.
    """
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def test_connection(self, credentials: Any) -> Dict[str, Any]:
        """Verify API credentials and return account details or error"""
        pass

    @abstractmethod
    def fetch_insights(
        self,
        client: ClientProfile,
        start_date: str,
        end_date: str
    ) -> List[UnifiedAdRecord]:
        """Fetch and return unified ad records for the date window"""
        pass
