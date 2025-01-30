import unittest
from functools import partial
from messages.workflow_message import WorkflowMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.action_message import ActionMessage
from resources.memory_resource import MemoryResourceConfig, MemoryResource, MemoryTruncationFunctions
from unittest.mock import patch

class TestMemoryResource(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Stop saving for workflow messages."""
        cls.patcher = patch("messages.workflow_message.WorkflowMessage.save", lambda *args, **kwargs: None)
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        """
        Set up a basic message tree. 
        
        Workflow: 
            - Phase [0, 1]: 
                - Agent [0, 1]: 
                    - Action 
        """
        workflow_message = WorkflowMessage.initialize("test")

        prev_phase = None 
        for i in range(2):
            phase_id = f'phase_{i}'
            phase_message = PhaseMessage(phase_id=phase_id, prev=prev_phase, agent_messages=[])
            prev_phase = phase_message
            
            initial_prompt = AgentMessage('system', 'initial prompt')
            phase_message.add_agent_message(initial_prompt)

            prev_agent = initial_prompt
            for j in range(2): 
                agent_id = agent_message = f'phase_{i}_agent_{j}'
                agent_message = AgentMessage(agent_id=agent_id, message=agent_message, prev=prev_agent)
                prev_agent = agent_message

                action_id = action_message = f'phase_{i}_agent_{j}_action'
                action_message = ActionMessage(resource_id=action_id, message=action_message)
                
                agent_message.add_action_message(action_message)
                phase_message.add_agent_message(agent_message)

            self._last_action_message = action_message
            self._last_agent_message = agent_message

            workflow_message.add_phase_message(phase_message)
        
        self._last_phase_message = phase_message

        self.config = MemoryResourceConfig(
            fmt="{prev_phase_messages}!!{prev_agent_messages}!!{prev_action_messages}",
            collate_fn=lambda x: ' '.join(x),
            segment_trunc_fn=MemoryTruncationFunctions.segment_fn_noop,
            memory_trunc_fn=MemoryTruncationFunctions.memory_fn_noop)
              
        self.memory = MemoryResource('memory', self.config)

    def test_get_memory_from_last_phase_message(self): 
        """
        Given the latest phase message (phase_1), reconstruct memory. 
        The memory should only contain previous phase messages (phase_0*),
        but current phase past agent or action messages should be N/A.
        """
        memory = self.memory.get_memory(self._last_phase_message).memory
        memory_without_prompt = memory.replace('initial prompt\n\n', '')
        memory_segments = memory_without_prompt.split('!!') 

        expected_prev_phases_memory = [
            '[phase_0_agent_0]phase_0_agent_0',
            '[phase_0_agent_0]phase_0_agent_0_action',
            '[phase_0_agent_1]phase_0_agent_1',
            '[phase_0_agent_1]phase_0_agent_1_action'
        ]

        self.assertEqual(memory_segments[0], ' '.join(expected_prev_phases_memory))
        self.assertEqual(memory_segments[1:], ['N/A', 'N/A'])
    
    def test_get_memory_from_last_agent_message(self): 
        """
        Given the latest agent message (phase_1, agent_1), reconstruct memory.
        The memory should contain previous phase messages (phase_0*)
        as well as previous agent messages in current phase (phase_1_agent*)
        but current agent, past action messages should be N/A.

        Note that the latest agent message (phase_1, agent_1) is added to the 
        prev_agents_memory.
        """
        memory = self.memory.get_memory(self._last_agent_message).memory

        memory_without_prompt = memory.replace('initial prompt\n\n', '')
        memory_segments = memory_without_prompt.split('!!') 

        expected_prev_phases_memory = [
            '[phase_0_agent_0]phase_0_agent_0',
            '[phase_0_agent_0]phase_0_agent_0_action', 
            '[phase_0_agent_1]phase_0_agent_1',
            '[phase_0_agent_1]phase_0_agent_1_action',
        ]

        self.assertEqual(memory_segments[0], ' '.join(expected_prev_phases_memory))

        expected_prev_agents_memory = [
            '[phase_1_agent_0]phase_1_agent_0', 
            '[phase_1_agent_0]phase_1_agent_0_action',
            '[phase_1_agent_1]phase_1_agent_1'
        ]

        self.assertEqual(memory_segments[1], ' '.join(expected_prev_agents_memory))
        self.assertEqual(memory_segments[-1], 'N/A')
    
    def test_get_memory_from_last_action_message(self):
        """
        Given the latest action message (phase_1, agent_1, action), reconstruct memory.
        The memory should contain previous phase messages (phase_0_*)
        as well as previous agent messages in current phase (phase_1_agent_0*)
        and current agent, past action messages (phase_1_agent_1*)

        Note that here, phase_1_agent_1 is in prev_actions memory.
        """ 
        memory = self.memory.get_memory(self._last_action_message).memory
        memory_without_prompt = memory.replace('initial prompt\n\n', '')
        memory_segments = memory_without_prompt.split('!!') 

        expected_prev_phases_memory = [
            '[phase_0_agent_0]phase_0_agent_0',
            '[phase_0_agent_0]phase_0_agent_0_action', 
            '[phase_0_agent_1]phase_0_agent_1',
            '[phase_0_agent_1]phase_0_agent_1_action',
        ]

        self.assertEqual(memory_segments[0], ' '.join(expected_prev_phases_memory))

        expected_prev_agents_memory = [
            '[phase_1_agent_0]phase_1_agent_0', 
            '[phase_1_agent_0]phase_1_agent_0_action',
        ]

        self.assertEqual(memory_segments[1], ' '.join(expected_prev_agents_memory))

        expected_prev_actions_memory = [
            '[phase_1_agent_1]phase_1_agent_1',
            '[phase_1_agent_1]phase_1_agent_1_action'
        ]

        self.assertEqual(memory_segments[-1], ' '.join(expected_prev_actions_memory))

    def test_config_validation(self):
        """
        Check that erroneous configurations are properly flagged.
        """
        # Workflow scope should include other messages
        faulty_fmt_lacking_kwargs = "{prev_agent_messages}" 
        # Format string should include a defined set of kwargs
        faulty_fmt_bad_kwargs = "{random_kwarg}"

        # Collate function should convert list of messages to string
        faulty_collate_fn = lambda x: x 
        # Segment truncation function should return a list of truncated messages
        faulty_segment_trunc_fn = lambda x: ' '.join(x)
        # Memory truncation function should return a list of truncated segments
        faulty_memory_trunc_fn = lambda x: [' '.join(y) for y in x]

        checks = {
            'fmt': faulty_fmt_lacking_kwargs,
            'fmt': faulty_fmt_bad_kwargs, 
            'collate_fn': faulty_collate_fn, 
            'segment_trunc_fn': faulty_segment_trunc_fn, 
            'memory_trunc_fn': faulty_memory_trunc_fn
        }

        for kw, check in checks.items(): 
            with self.assertRaises((AssertionError, ValueError)): 
                _ = MemoryResourceConfig(**{kw: check})
    
    def test_segment_truncation_by_message(self):
        """
        Check that each segment is truncated except for the very last input.
        """
        self.config.segment_trunc_fn = partial(MemoryTruncationFunctions.segment_fn_last_n, n=1)
        trunc_memory = MemoryResource('memory_1', self.config)

        memory = trunc_memory.get_memory(self._last_action_message).memory
        memory_without_prompt = memory.replace('initial prompt\n\n', '')
        memory_segments = memory_without_prompt.split('!!') 

        expected_prev_phases_memory = [
            '<TRUNC>',
            '[phase_0_agent_1]phase_0_agent_1_action',
        ]

        self.assertEqual(memory_segments[0], ' '.join(expected_prev_phases_memory))

        expected_prev_agents_memory = [
            '<TRUNC>',
            '[phase_1_agent_0]phase_1_agent_0_action',
        ]

        self.assertEqual(memory_segments[1], ' '.join(expected_prev_agents_memory))

        expected_prev_actions_memory = [
            '<TRUNC>',
            '[phase_1_agent_1]phase_1_agent_1_action'
        ]

        self.assertEqual(memory_segments[-1], ' '.join(expected_prev_actions_memory))

    def test_memory_truncation_by_token(self):
        """
        Check that each segment only contains a single token after truncation.
        """
        og_memory = self.memory.get_memory(self._last_action_message).memory 
        memory_without_prompt = ''.join(og_memory.split('\n\n')[1:])
        memory_segments = memory_without_prompt.split('!!')

        self.assertTrue(all(len(x.split()) > 1 for x in memory_segments))

        self.config.memory_trunc_fn = partial(MemoryTruncationFunctions.memory_fn_by_token, max_input_tokens=3)
        trunc_memory = MemoryResource('memory_1', self.config).get_memory(self._last_action_message).memory
        trunc_memory_without_prompt = ''.join(trunc_memory.split('\n\n')[1:])
        trunc_memory_segments = trunc_memory_without_prompt.split('!!')
        
        self.assertTrue(all(len(x.split()) == 1 for x in trunc_memory_segments))
    
    def test_messages_with_version(self):
        agent0 = self._last_agent_message.prev 

        new_agent0 = AgentMessage('new_agent_0', 'new_agent_0')

        new_agent0.set_prev(agent0.prev)
        new_agent0.set_next(agent0.next)
        agent0.parent.add_agent_message(new_agent0)

        new_agent0.set_version_prev(agent0)
        
        memory = self.memory.get_memory(new_agent0).memory

        self.assertNotIn(agent0._message, memory)
        self.assertIn(new_agent0._message, memory)

    def test_pin(self):
        """
        Check that pinning retains message in memory.
        """
        self.config.segment_trunc_fn = partial(MemoryTruncationFunctions.segment_fn_last_n, n=1)
        trunc_memory = MemoryResource('memory_1', self.config)

        memory = trunc_memory.get_memory(self._last_action_message).memory
        self.assertNotIn('phase_0_agent_0', memory)

        trunc_memory.pin('phase_0_agent_0')

        memory = trunc_memory.get_memory(self._last_action_message).memory
        self.assertIn('phase_0_agent_0', memory)
    
    def test_pin_non_truncated(self): 
        """
        Check that pinning non-truncated memory does not cause duplicates.
        """
        memory = self.memory.get_memory(self._last_action_message).memory
        self.assertIn('phase_0_agent_0_action', memory)
        self.memory.pin('phase_0_agent_0_action')

        memory = self.memory.get_memory(self._last_action_message).memory

        start = 0
        cnt = 0
        while (start := memory.find('phase_0_agent_0_action', start)) >= 0:
            start = start + 1
            cnt += 1
        
        self.assertEqual(cnt, 1)
        



if __name__ == '__main__': 
    unittest.main()

