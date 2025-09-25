"""Application data model for the initializer system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Application:
    """Represents an application that can be installed."""
    name: str
    package: str
    description: str = ""
    category: str = ""
    post_install: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    recommended: bool = False
    installed: bool = False
    executables: List[str] = field(default_factory=list)
    type: str = "standalone"  # "standalone" or "component"

    def get_package_list(self) -> List[str]:
        """Get list of packages from the package string."""
        return self.package.split()