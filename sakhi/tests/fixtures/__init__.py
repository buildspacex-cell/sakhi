"""
Test fixtures and factories for Sakhi tests.

This module provides:
- Demo user constants
- Factory functions for creating test data
- Database helpers for integration tests
- Mock fixtures for unit tests

Usage:
    from sakhi.tests.fixtures import (
        DEMO_USER_ID,
        get_test_person_id,
        create_test_journal_entry,
        ensure_test_user,
    )
"""

from .factories import *
from .constants import *
from .helpers import *
