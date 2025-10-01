"""Segment state management - unified data structure for segment states.

This module provides a clean data structure to replace scattered cache and loading
state management across the MainMenu class, following the principle:
"Bad programmers worry about the code. Good programmers worry about data structures."
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class SegmentState:
    """Unified state container for a single segment.

    Replaces scattered reactive attributes like:
    - system_info_cache, system_info_loading
    - homebrew_cache, homebrew_loading
    - etc.

    Attributes:
        name: Segment identifier (e.g., "system_info", "homebrew")
        loading: Whether data is currently being loaded
        cache: Cached data for this segment
        error: Error message if loading failed
    """
    name: str
    loading: bool = False
    cache: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def is_loaded(self) -> bool:
        """Check if segment data is loaded and available."""
        return self.cache is not None and not self.loading and self.error is None

    def has_error(self) -> bool:
        """Check if segment encountered an error."""
        return self.error is not None

    def is_loading(self) -> bool:
        """Check if segment is currently loading."""
        return self.loading

    def start_loading(self) -> None:
        """Mark segment as loading."""
        self.loading = True
        self.error = None

    def finish_loading(self, cache: Dict[str, Any]) -> None:
        """Mark loading complete with cached data."""
        self.loading = False
        self.cache = cache
        self.error = None

    def set_error(self, error: str) -> None:
        """Set error state."""
        self.loading = False
        self.error = error
        self.cache = None

    def clear(self) -> None:
        """Clear all state."""
        self.loading = False
        self.cache = None
        self.error = None


class SegmentStateManager:
    """Manager for all segment states.

    Centralizes state management and eliminates special cases by providing
    a unified interface for all segments.
    """

    def __init__(self, segment_ids: list[str]):
        """Initialize state manager with segment IDs.

        Args:
            segment_ids: List of segment identifiers to manage
        """
        self.states: Dict[str, SegmentState] = {
            segment_id: SegmentState(name=segment_id)
            for segment_id in segment_ids
        }

    def get_state(self, segment_id: str) -> Optional[SegmentState]:
        """Get state for a specific segment.

        Args:
            segment_id: Segment identifier

        Returns:
            SegmentState if found, None otherwise
        """
        return self.states.get(segment_id)

    def is_loading(self, segment_id: str) -> bool:
        """Check if segment is loading.

        Args:
            segment_id: Segment identifier

        Returns:
            True if loading, False otherwise
        """
        state = self.get_state(segment_id)
        return state.is_loading() if state else False

    def is_loaded(self, segment_id: str) -> bool:
        """Check if segment is loaded.

        Args:
            segment_id: Segment identifier

        Returns:
            True if loaded, False otherwise
        """
        state = self.get_state(segment_id)
        return state.is_loaded() if state else False

    def has_error(self, segment_id: str) -> bool:
        """Check if segment has error.

        Args:
            segment_id: Segment identifier

        Returns:
            True if has error, False otherwise
        """
        state = self.get_state(segment_id)
        return state.has_error() if state else False

    def get_cache(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """Get cached data for segment.

        Args:
            segment_id: Segment identifier

        Returns:
            Cached data if available, None otherwise
        """
        state = self.get_state(segment_id)
        return state.cache if state else None

    def start_loading(self, segment_id: str) -> None:
        """Mark segment as loading.

        Args:
            segment_id: Segment identifier
        """
        state = self.get_state(segment_id)
        if state:
            state.start_loading()

    def finish_loading(self, segment_id: str, cache: Dict[str, Any]) -> None:
        """Mark segment loading complete.

        Args:
            segment_id: Segment identifier
            cache: Cached data
        """
        state = self.get_state(segment_id)
        if state:
            state.finish_loading(cache)

    def set_error(self, segment_id: str, error: str) -> None:
        """Set error for segment.

        Args:
            segment_id: Segment identifier
            error: Error message
        """
        state = self.get_state(segment_id)
        if state:
            state.set_error(error)

    def clear_all(self) -> None:
        """Clear all segment states."""
        for state in self.states.values():
            state.clear()

    def clear(self, segment_id: str) -> None:
        """Clear specific segment state.

        Args:
            segment_id: Segment identifier
        """
        state = self.get_state(segment_id)
        if state:
            state.clear()