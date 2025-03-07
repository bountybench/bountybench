import random
import string
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.agent_manager import AgentConfig, AgentManager
from agents.executor_agent.executor_agent import ExecutorAgent
from agents.exploit_agent.exploit_agent import ExploitAgent, ExploitAgentConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from resources.base_resource import BaseResource
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from tests.agents.agent_test_utils import EnvPath, lunary_bounty_0_setup


@pytest.fixture(scope="module")
def agent_configs(lunary_bounty_0_setup):
    env_setup: EnvPath = lunary_bounty_0_setup
    pConfig = PatchAgentConfig(
        bounty_dir=env_setup.BOUNTY_DIR,
        task_dir=env_setup.TASK_DIR,
        use_verify_script=False,
    )
    eConfig = ExploitAgentConfig(
        bounty_dir=env_setup.BOUNTY_DIR,
        task_dir=env_setup.TASK_DIR,
        tmp_dir=env_setup.TMP_DIR,
    )
    return pConfig, eConfig


@pytest.fixture(scope="module")
def alternative_agent_configs():
    bounty_dir = "bounties/bounty0"
    task_dir = "lunary"
    tmp_dir = "lunary/bounties/bounty0/tmp_1"
    pConfig = PatchAgentConfig(
        bounty_dir=bounty_dir, task_dir=task_dir, use_verify_script=False
    )
    eConfig = ExploitAgentConfig(
        bounty_dir=bounty_dir,
        task_dir=task_dir,
        tmp_dir=tmp_dir
    )
    return pConfig, eConfig


@pytest.fixture(scope="module")
def initialized_agent_manager(agent_configs):
    am = AgentManager(workflow_id="1")
    pConfig, eConfig = agent_configs
    am.initialize_phase_agents(
        {"exploit_agent": (ExploitAgent, eConfig), "patch_agent": (PatchAgent, pConfig)}
    )
    yield am
    am.deallocate_all_agents()


def test_register_agent(agent_configs):
    am = AgentManager(workflow_id="1")
    am.register_agent("test", PatchAgent, agent_configs[0])

    assert len(am._agent_configs) == 1
    assert "test" in am._agent_configs
    assert isinstance(am._agent_configs, dict)
    assert isinstance(am._agent_configs["test"], tuple)
    assert len(am._agent_configs["test"]) == 2
    assert (am._agent_configs["test"][0]) == PatchAgent
    assert (am._agent_configs["test"][1]) == agent_configs[0]


def test_initialize_phase_agents_success(agent_configs, initialized_agent_manager):
    am = AgentManager(workflow_id="1")
    pConfig, eConfig = agent_configs
    agent_configs = {
        "exploit_agent": (ExploitAgent, eConfig),
        "patch_agent": (PatchAgent, pConfig),
    }
    initialized_agents = am.initialize_phase_agents(agent_configs)
    assert len(initialized_agents) == 2
    assert len(am._agents) == 2
    assert len(am._phase_agents) == 2
    for a_id, a_agent in initialized_agents:
        assert a_id in agent_configs.keys()
        if a_id == "exploit_agent":
            assert isinstance(a_agent, ExploitAgent)
        elif a_id == "patch_agent":
            assert isinstance(a_agent, PatchAgent)
        else:
            assert False


def test_initialize_phase_agents_mismatch(
    agent_configs, alternative_agent_configs, initialized_agent_manager
):
    am = AgentManager(workflow_id="1")
    pConfig, eConfig = agent_configs
    pAltConfig, eAltConfig = alternative_agent_configs
    agent_configs = {
        "exploit_agent": (ExploitAgent, eConfig),
        "patch_agent": (PatchAgent, pConfig),
    }
    agent_alt_configs = {
        "exploit_agent": (ExploitAgent, eAltConfig),
        "patch_agent": (PatchAgent, pAltConfig),
    }
    am.initialize_phase_agents(agent_configs)
    with pytest.raises(
        ValueError, match=f"Agent exploit_agent exists with different configuration"
    ):
        am.initialize_phase_agents(agent_alt_configs)


def test_initialize_phase_agents_mismatch(agent_configs, initialized_agent_manager):
    am = AgentManager(workflow_id="1")
    pConfig, eConfig = agent_configs
    agent_configs = {
        "exploit_agent": (ExploitAgent, eConfig),
        "patch_agent": (PatchAgent, pConfig),
    }

    def mock_create_agent(self, agent_id, agent_class, agent_config):
        raise ValueError

    with pytest.raises(Exception):
        with patch.object(AgentManager, "create_agent", mock_create_agent):
            am.initialize_phase_agents(agent_configs)


def test_update_phase_agents_models_has_executor():
    mock_model_resource_config = MagicMock()
    mock_model_resource = MagicMock(return_value=None)

    ModelResourceConfig.create = MagicMock(return_value=mock_model_resource_config)
    ModelResource.__init__ = mock_model_resource
    ModelResource.to_dict = MagicMock()

    am = AgentManager(workflow_id=1)

    class Model:
        def to_dict(self):
            return ""

    am._phase_agents = {
        "executor": ExecutorAgent("update_phase_agents_has_executor", AgentConfig)
    }
    for agent in am._phase_agents.values():
        agent.model = Model()

    new_model = "new_model_value"
    am.update_phase_agents_models(new_model)

    # Assertions
    for agent in am._phase_agents.values():
        mock_model_resource.assert_called_with("model", mock_model_resource_config)
        assert hasattr(agent, "model")
        assert isinstance(agent.model, ModelResource)
        ModelResourceConfig.create.assert_called_with(model=new_model)


def test_update_phase_agents_models_no_executor():
    mock_model_resource_config = MagicMock()
    model_resource_mock = MagicMock(return_value=None)

    ModelResourceConfig.create = MagicMock(return_value=mock_model_resource_config)
    ModelResource.__init__ = model_resource_mock

    am = AgentManager(workflow_id=1)
    am._phase_agents = {
        "patch_agent": PatchAgent(
            "update_phase_agents_no_executor", PatchAgentConfig(Path(), Path(), False)
        )
    }

    new_model = "new_model_value"
    am.update_phase_agents_models(new_model)

    for agent in am._phase_agents.values():
        if isinstance(agent, PatchAgent):
            model_resource_mock.assert_not_called()
            ModelResourceConfig.create.assert_not_called()
            assert not hasattr(agent, "model")


def test_create_agent(agent_configs, initialized_agent_manager):
    pConfig, _ = agent_configs
    am = AgentManager(workflow_id="1")
    agent = am.create_agent(".", PatchAgent, pConfig)

    assert isinstance(agent, PatchAgent)
    assert hasattr(agent, "init_files")
    assert hasattr(agent, "docker")
    assert hasattr(agent, "repo_setup")
    assert not hasattr(agent, "bounty_setup")


def test_bind_resources_to_agent(agent_configs, initialized_agent_manager):
    pConfig, _ = agent_configs
    am = AgentManager(workflow_id="1")
    agent = PatchAgent(".", pConfig)
    am.bind_resources_to_agent(agent)

    assert hasattr(agent, "init_files")
    assert hasattr(agent, "docker")
    assert hasattr(agent, "repo_setup")
    assert not hasattr(agent, "bounty_setup")


def test_parse_resource_entry():
    am = AgentManager(workflow_id="1")

    def generate_random_string(length=10):
        letters_and_digits = string.ascii_letters + string.digits
        random_string = "".join(
            random.choice(letters_and_digits) for i in range(length)
        )
        return random_string

    resources = {
        BaseResource: "baseresource",
        DockerResource: "dockerresource",
        InitFilesResource: "initfilesresource",
        KaliEnvResource: "kalienvresource",
    }
    for resource, name in resources.items():
        result = am._parse_resource_entry(resource)
        assert result[0] == resource and result[1] == None

    for resource in resources.keys():
        name = generate_random_string()
        result = am._parse_resource_entry((resource, name))
        assert result[0] == resource and result[1] == name


def test_is_agent_equivalent(initialized_agent_manager, agent_configs) -> bool:
    pConfig, eConfig = agent_configs
    am: AgentManager = initialized_agent_manager

    assert not am.is_agent_equivalent("bad agent", PatchAgent, pConfig)
    assert not am.is_agent_equivalent("bad agent", ExploitAgent, eConfig)
    assert not am.is_agent_equivalent(
        "exploit_agent",
        ExploitAgent,
        ExploitAgentConfig(Path("bountyagent"), Path("bountyagent"), Path("bountyagent")),
    )
    assert not am.is_agent_equivalent(
        "patch_agent",
        PatchAgent,
        PatchAgentConfig(Path("bountyagent"), Path("bountyagent"), False),
    )
    assert am.is_agent_equivalent("patch_agent", PatchAgent, pConfig)
    assert am.is_agent_equivalent("exploit_agent", ExploitAgent, eConfig)


def test_get_agent(initialized_agent_manager):
    am: AgentManager = initialized_agent_manager
    bad_agent = "bad_agent"
    with pytest.raises(KeyError, match=f"Agent '{bad_agent}' not initialized"):
        am.get_agent(bad_agent)

    assert isinstance(am.get_agent("exploit_agent"), ExploitAgent)
    assert isinstance(am.get_agent("patch_agent"), PatchAgent)


def test_deallocate_all_agents():
    am: AgentManager = AgentManager(workflow_id=1)
    am.deallocate_all_agents()

    am._agents = {"1": list(), "2": list(), "3": list()}
    am._phase_agents = {"1": 1, "2": 1, "3": 1}
    am._agent_configs = {"1": 1, "2": 1, "3": 1}
    am.deallocate_all_agents()
    assert len(am._agents) == 0
    assert len(am._phase_agents) == 0
    assert len(am._agent_configs) == 0
