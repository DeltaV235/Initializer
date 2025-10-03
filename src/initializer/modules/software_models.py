"""Software management data models for mixed suite and standalone applications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


class SoftwareItem(ABC):
    """Base class for all software items (suites or standalone applications)."""

    @abstractmethod
    def get_display_name(self) -> str:
        """Get display name for UI rendering."""
        pass

    @abstractmethod
    def get_install_status(self) -> str:
        """Get install status display string."""
        pass

    @abstractmethod
    def is_expandable(self) -> bool:
        """Check if this item can be expanded in UI."""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """Get item type (suite/standalone/component)."""
        pass


@dataclass
class Application(SoftwareItem):
    """Represents an application that can be installed (standalone or component)."""
    name: str
    package: str
    executables: List[str] = field(default_factory=list)
    description: str = ""
    category: str = ""
    post_install: str = ""
    tags: List[str] = field(default_factory=list)
    install_recommends: bool = None  # None means use global config, True/False overrides
    installed: bool = False
    type: str = "standalone"  # "standalone" or "component"

    def get_display_name(self) -> str:
        """Get display name for UI."""
        if self.type == "component":
            return f"├─ {self.name}"
        return self.name

    def get_install_status(self) -> str:
        """Get install status display string."""
        if self.installed:
            return "[green]✓[/green]"
        return "[bright_black]○[/bright_black]"

    def is_expandable(self) -> bool:
        """Applications are not expandable."""
        return False

    def get_type(self) -> str:
        """Get item type."""
        return self.type

    def get_package_list(self) -> List[str]:
        """Get list of packages from the package string."""
        return self.package.split()


@dataclass
class ApplicationSuite(SoftwareItem):
    """Represents a software suite containing multiple related applications."""
    name: str
    description: str
    category: str
    components: List[Application] = field(default_factory=list)
    expanded: bool = False
    type: str = "suite"

    def get_display_name(self) -> str:
        """Get display name with expansion indicator."""
        icon = "▼" if self.expanded else "▶"
        return f"{icon} {self.name}"

    def get_install_status(self) -> str:
        """Get install status with component count."""
        installed_count = sum(1 for component in self.components if component.installed)
        total_count = len(self.components)

        if installed_count == 0:
            return f"[bright_black]○ 0/{total_count}[/bright_black]"
        elif installed_count == total_count:
            return f"[green]● {total_count}/{total_count}[/green]"
        else:
            return f"[yellow]◐ {installed_count}/{total_count}[/yellow]"

    def is_expandable(self) -> bool:
        """Suites are expandable."""
        return True

    def get_type(self) -> str:
        """Get item type."""
        return self.type

    @property
    def install_status_type(self) -> str:
        """Get install status type for logic decisions."""
        installed_count = sum(1 for component in self.components if component.installed)
        total_count = len(self.components)

        if installed_count == 0:
            return "not_installed"
        elif installed_count == total_count:
            return "fully_installed"
        else:
            return "partially_installed"

    def get_all_packages(self) -> List[str]:
        """Get all packages from all components."""
        packages = []
        for component in self.components:
            packages.extend(component.get_package_list())
        return packages

    def get_uninstalled_components(self) -> List[Application]:
        """Get list of components that are not installed."""
        return [component for component in self.components if not component.installed]

    def get_installed_components(self) -> List[Application]:
        """Get list of components that are installed."""
        return [component for component in self.components if component.installed]