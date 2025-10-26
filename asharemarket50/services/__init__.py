"""External service integrations for the CSI 50 simulator."""

from .akshare_client import AKShareClient, AKShareUnavailable

__all__ = ["AKShareClient", "AKShareUnavailable"]
