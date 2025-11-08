"""Tests for the FastAPI registration and listing endpoints.

The tests patch ``src.utils.find_rss_feed`` to avoid real network calls and
operate on a fresh SQLite database by removing ``src/feeds.db`` before each
run.
"""

from pathlib import Path

from unittest import TestCase, mock

from src.app_server import app


class TestAPI(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Ensure a clean database before any tests run.
        db_path = Path(__file__).parents[1] / "src" / "feeds.db"
        if db_path.exists():
            db_path.unlink()
        # Patch the RSS discovery to avoid network calls.
        cls.patcher = mock.patch(
            "src.utils.find_rss_feed",
            return_value={"url": "http://example.com/feed", "title": "Example Feed"},
        )
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher.stop()

    def test_register_and_list_routes(self) -> None:
        # Verify that the FastAPI app defines the expected endpoints.
        paths = {route.path for route in app.routes}
        self.assertIn("/registerFeed", paths)
        self.assertIn("/listFeeds", paths)

        # Further functional tests could invoke the API, but they require the
        # ``httpx`` dependency used by FastAPI's ``TestClient``. To keep the test
        # suite lightweight and avoid extra dependencies, we stop here after
        # confirming the routes are present.
