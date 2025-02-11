import unittest

from resources.model_resource.model_resource import ModelResourceConfig


class TestAgentConfigs(unittest.TestCase):

    def test_agent_lm_config(self):
        # Test default configuration
        lm_config1 = ModelResourceConfig()
        self.assertEqual(lm_config1.model, "openai/o3-mini-2025-01-14")
        self.assertEqual(lm_config1.max_output_tokens, 4096)
        self.assertFalse(lm_config1.use_helm)

        # Test custom configuration
        lm_config2 = ModelResourceConfig.create(
            model="custom-model", max_output_tokens=10000
        )
        self.assertEqual(lm_config2.model, "custom-model")
        self.assertEqual(lm_config2.max_output_tokens, 10000)
        self.assertTrue(lm_config2.use_helm)

        # Test Claude model configuration
        lm_config3 = ModelResourceConfig.create(model="claude-v1")
        self.assertEqual(lm_config3.model, "claude-v1")
        self.assertTrue(lm_config3.use_helm)


if __name__ == "__main__":
    unittest.main()
