"""CEC service calculation package."""
from importlib import metadata

__all__ = ["__version__"]
try:
    __version__ = metadata.version("BuildingServiceTools")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback for local runs
    __version__ = "0.0.0"
