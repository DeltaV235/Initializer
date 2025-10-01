"""Main menu submodule - modularized components."""

from .segment_state import SegmentState, SegmentStateManager
from .data_loaders import SegmentDisplayRenderer
from .app_page_manager import AppPageManager
from .pm_interaction_manager import PackageManagerInteractionManager
from .app_interaction_manager import AppInstallInteractionManager

__all__ = [
    "SegmentState",
    "SegmentStateManager",
    "SegmentDisplayRenderer",
    "AppPageManager",
    "PackageManagerInteractionManager",
    "AppInstallInteractionManager",
]
