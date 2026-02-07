"""Unit tests for email sync worker task."""

from unittest.mock import AsyncMock, patch

import pytest

from sakhi.apps.api.services.email.models import SyncProgress, SyncStatus


class TestEmailSyncWorker:
    """Tests for the email sync worker."""

    @pytest.mark.asyncio
    async def test_successful_sync_and_extraction(self):
        """Should sync then extract signals on success."""
        mock_progress = SyncProgress(
            status=SyncStatus.INCREMENTAL_SYNC,
            messages_synced=150,
            current_phase="complete",
        )

        with patch(
            "sakhi.apps.worker.tasks.email_sync_worker.start_email_sync",
            new_callable=AsyncMock,
            return_value=mock_progress,
        ) as mock_sync, patch(
            "sakhi.apps.worker.tasks.email_sync_worker.extract_all_signals",
            new_callable=AsyncMock,
            return_value={"status": "extracted"},
        ) as mock_extract:
            from sakhi.apps.worker.tasks.email_sync_worker import _run_email_sync

            result = await _run_email_sync("test-person-id")

            mock_sync.assert_called_once_with("test-person-id")
            mock_extract.assert_called_once_with(
                "test-person-id", force_refresh=True
            )
            assert result["status"] == "complete"
            assert result["messages_synced"] == 150

    @pytest.mark.asyncio
    async def test_sync_error_skips_extraction(self):
        """Should not extract signals when sync fails."""
        mock_progress = SyncProgress(
            status=SyncStatus.ERROR,
            error="Token expired",
        )

        with patch(
            "sakhi.apps.worker.tasks.email_sync_worker.start_email_sync",
            new_callable=AsyncMock,
            return_value=mock_progress,
        ), patch(
            "sakhi.apps.worker.tasks.email_sync_worker.extract_all_signals",
            new_callable=AsyncMock,
        ) as mock_extract:
            from sakhi.apps.worker.tasks.email_sync_worker import _run_email_sync

            result = await _run_email_sync("test-person-id")

            mock_extract.assert_not_called()
            assert result["status"] == "error"
            assert "Token expired" in (result.get("error") or "")

    @pytest.mark.asyncio
    async def test_revoked_status_skips_extraction(self):
        """Should not extract signals when access is revoked."""
        mock_progress = SyncProgress(
            status=SyncStatus.REVOKED,
            error="Access revoked by user",
        )

        with patch(
            "sakhi.apps.worker.tasks.email_sync_worker.start_email_sync",
            new_callable=AsyncMock,
            return_value=mock_progress,
        ), patch(
            "sakhi.apps.worker.tasks.email_sync_worker.extract_all_signals",
            new_callable=AsyncMock,
        ) as mock_extract:
            from sakhi.apps.worker.tasks.email_sync_worker import _run_email_sync

            result = await _run_email_sync("test-person-id")

            mock_extract.assert_not_called()
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Should catch exceptions and update sync status."""
        with patch(
            "sakhi.apps.worker.tasks.email_sync_worker.start_email_sync",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection failed"),
        ), patch(
            "sakhi.apps.worker.tasks.email_sync_worker.update_sync_status",
            new_callable=AsyncMock,
        ) as mock_update:
            from sakhi.apps.worker.tasks.email_sync_worker import _run_email_sync

            result = await _run_email_sync("test-person-id")

            assert result["status"] == "error"
            assert "Connection failed" in result["error"]
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_initial_sync_status_succeeds(self):
        """Should succeed with INITIAL_SYNC status."""
        mock_progress = SyncProgress(
            status=SyncStatus.INITIAL_SYNC,
            messages_synced=500,
            current_phase="complete",
        )

        with patch(
            "sakhi.apps.worker.tasks.email_sync_worker.start_email_sync",
            new_callable=AsyncMock,
            return_value=mock_progress,
        ), patch(
            "sakhi.apps.worker.tasks.email_sync_worker.extract_all_signals",
            new_callable=AsyncMock,
            return_value={"status": "extracted"},
        ) as mock_extract:
            from sakhi.apps.worker.tasks.email_sync_worker import _run_email_sync

            result = await _run_email_sync("test-person-id")

            mock_extract.assert_called_once()
            assert result["status"] == "complete"
            assert result["messages_synced"] == 500
