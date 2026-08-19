"""
Test: READ-ONLY Elasticsearch verb allowlist (Constraint #2)

Verifies that the ES client constants correctly define which HTTP methods
and endpoints are allowed, and that forbidden endpoints are comprehensive.
"""

from __future__ import annotations

from tads.constants import (
    ES_ALLOWED_HTTP_METHODS,
    ES_ALLOWED_POST_ENDPOINTS,
    ES_FORBIDDEN_ENDPOINTS,
)


class TestESAllowedMethods:
    """Verify the HTTP method allowlist is correctly defined."""

    def test_only_get_and_post_allowed(self) -> None:
        """Only GET and POST should be in the allowlist."""
        assert frozenset({"GET", "POST"}) == ES_ALLOWED_HTTP_METHODS

    def test_put_not_allowed(self) -> None:
        """PUT is a mutating method and must not be allowed."""
        assert "PUT" not in ES_ALLOWED_HTTP_METHODS

    def test_delete_not_allowed(self) -> None:
        """DELETE is a mutating method and must not be allowed."""
        assert "DELETE" not in ES_ALLOWED_HTTP_METHODS

    def test_patch_not_allowed(self) -> None:
        """PATCH is a mutating method and must not be allowed."""
        assert "PATCH" not in ES_ALLOWED_HTTP_METHODS


class TestESAllowedPostEndpoints:
    """Verify that POST is only allowed for search-related endpoints."""

    def test_search_allowed(self) -> None:
        assert "_search" in ES_ALLOWED_POST_ENDPOINTS

    def test_scroll_allowed(self) -> None:
        assert "_scroll" in ES_ALLOWED_POST_ENDPOINTS

    def test_pit_allowed(self) -> None:
        assert "_pit" in ES_ALLOWED_POST_ENDPOINTS

    def test_bulk_not_in_allowed(self) -> None:
        """_bulk is a write operation and must not be in allowed endpoints."""
        assert "_bulk" not in ES_ALLOWED_POST_ENDPOINTS

    def test_update_not_in_allowed(self) -> None:
        """_update is a write operation."""
        assert "_update" not in ES_ALLOWED_POST_ENDPOINTS

    def test_delete_not_in_allowed(self) -> None:
        """_delete is a write operation."""
        assert "_delete" not in ES_ALLOWED_POST_ENDPOINTS

    def test_index_not_in_allowed(self) -> None:
        """_index is a write operation."""
        assert "_index" not in ES_ALLOWED_POST_ENDPOINTS


class TestESForbiddenEndpoints:
    """Verify that all mutating endpoints are explicitly forbidden."""

    def test_bulk_forbidden(self) -> None:
        assert "_bulk" in ES_FORBIDDEN_ENDPOINTS

    def test_update_forbidden(self) -> None:
        assert "_update" in ES_FORBIDDEN_ENDPOINTS

    def test_delete_forbidden(self) -> None:
        assert "_delete" in ES_FORBIDDEN_ENDPOINTS

    def test_index_forbidden(self) -> None:
        assert "_index" in ES_FORBIDDEN_ENDPOINTS

    def test_ilm_forbidden(self) -> None:
        assert "_ilm" in ES_FORBIDDEN_ENDPOINTS

    def test_reindex_forbidden(self) -> None:
        assert "_reindex" in ES_FORBIDDEN_ENDPOINTS

    def test_create_forbidden(self) -> None:
        assert "_create" in ES_FORBIDDEN_ENDPOINTS

    def test_no_overlap_with_allowed(self) -> None:
        """Forbidden and allowed endpoints must not overlap."""
        overlap = ES_FORBIDDEN_ENDPOINTS & ES_ALLOWED_POST_ENDPOINTS
        assert overlap == set(), f"Overlap found: {overlap}"
