import unittest
from agents.base_agent import AgentConfig
from agents.executor_agent.executor_agent import ExecutorAgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig

class TestAgentConfigs(unittest.TestCase):

    def test_agent_lm_config(self):
        # Test default configuration
        lm_config1 = AgentLMConfig()
        self.assertEqual(lm_config1.model, 'openai/o3-mini-2024-12-17')
        self.assertEqual(lm_config1.max_output_tokens, 5000)
        self.assertFalse(lm_config1.use_helm)

        # Test custom configuration
        lm_config2 = AgentLMConfig.create(model='custom-model', max_output_tokens=10000)
        self.assertEqual(lm_config2.model, 'custom-model')
        self.assertEqual(lm_config2.max_output_tokens, 10000)
        self.assertFalse(lm_config2.use_helm)

        # Test Claude model configuration
        lm_config3 = AgentLMConfig.create(model='claude-v1')
        self.assertEqual(lm_config3.model, 'claude-v1')
        self.assertTrue(lm_config3.use_helm)

    def test_executor_agent_config(self):
        # Test with custom id and target_host
        config1 = ExecutorAgentConfig(id="temp", target_host='example.com')
        self.assertEqual(config1.id, "temp")
        self.assertEqual(config1.target_host, 'example.com')

        # Test with default id
        config2 = ExecutorAgentConfig(target_host='another-host.com')
        self.assertEqual(config2.id, 'ExecutorAgentConfig')
        self.assertEqual(config2.target_host, 'another-host.com')

        # Test with all parameters overridden
        config3 = ExecutorAgentConfig(
            id="custom",
            lm_config=AgentLMConfig(model='gpt-4'),
            target_host='example.org',
            initial_prompt='Start here'
        )
        self.assertEqual(config3.id, "custom")
        self.assertEqual(config3.lm_config.model, 'gpt-4')
        self.assertEqual(config3.target_host, 'example.org')
        self.assertEqual(config3.initial_prompt, 'Start here')

        # Test with kwargs
        kwargs = {
            'id': 'kwarg-id',
            'target_host': 'kwarg-host.com',
            'lm_config': AgentLMConfig.create(max_output_tokens=8000, model='claude-v2')
        }
        config4 = ExecutorAgentConfig(**kwargs)
        self.assertEqual(config4.id, 'kwarg-id')
        self.assertEqual(config4.target_host, 'kwarg-host.com')
        self.assertEqual(config4.lm_config.max_output_tokens, 8000)
        self.assertEqual(config4.lm_config.model, 'claude-v2')
        self.assertTrue(config4.lm_config.use_helm)

        # Test with default LM config
        config5 = ExecutorAgentConfig(target_host='default-lm-host.com')
        self.assertEqual(config5.id, 'ExecutorAgentConfig')
        self.assertEqual(config5.target_host, 'default-lm-host.com')
        self.assertEqual(config5.lm_config.model, 'openai/o3-mini-2024-12-17')

if __name__ == '__main__':
    unittest.main()