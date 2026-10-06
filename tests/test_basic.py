"""Basic smoke and unit tests for AI News Aggregator."""

import unittest
from app.config import YOUTUBE_CHANNELS
from app.profiles.user_profile import USER_PROFILE
from app.database.models import OpenAIArticle, AnthropicArticle, YouTubeVideo, Digest


class TestBasicSetup(unittest.TestCase):
    def test_config(self):
        """Verify channel configurations."""
        self.assertIsInstance(YOUTUBE_CHANNELS, list)
        self.assertGreater(len(YOUTUBE_CHANNELS), 0)

    def test_user_profile_structure(self):
        """Verify user profile keys and preferences."""
        self.assertIn("name", USER_PROFILE)
        self.assertIn("interests", USER_PROFILE)
        self.assertIsInstance(USER_PROFILE["interests"], list)
        self.assertIn("preferences", USER_PROFILE)
        self.assertIsInstance(USER_PROFILE["preferences"], dict)

    def test_models_exist(self):
        """Verify database models are defined correctly."""
        self.assertTrue(hasattr(OpenAIArticle, "__tablename__"))
        self.assertTrue(hasattr(AnthropicArticle, "__tablename__"))
        self.assertTrue(hasattr(YouTubeVideo, "__tablename__"))
        self.assertTrue(hasattr(Digest, "__tablename__"))


if __name__ == "__main__":
    unittest.main()
