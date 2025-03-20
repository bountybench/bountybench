from messages.agent_messages.agent_message import AgentMessage


class PatchAgentMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: str,
        success: bool = False,
        patch_files_dir: str = None,
        prev: AgentMessage = None,
    ) -> None:
        super().__init__(agent_id=agent_id, message=message, prev=prev)
        self._success = success
        self._patch_files_dir = patch_files_dir
        self._repo_invariant_scores = {}
        self._bounty_invariant_scores = {}

    @property
    def success(self) -> bool:
        return self._success

    def set_success(self, value: bool):
        self._success = value

    def set_repo_invariant_scores(self, value: dict):
        self._repo_invariant_scores = value

    def set_bounty_invariant_scores(self, value: dict):
        self._bounty_invariant_scores = value

    @property
    def patch_files_dir(self) -> str:
        return self._patch_files_dir

    @property
    def repo_invariant_scores(self) -> dict:
        return self._repo_invariant_scores

    @property
    def bounty_invariant_scores(self) -> dict:
        return self._bounty_invariant_scores

    def set_patch_files_path(self, value: str):
        self._patch_files_dir = value

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        base_dict.update(
            {
                "success": self.success,
                "patch_files_dir": self.patch_files_dir,
            }
        )
        return base_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        base_dict.update(
            {
                "success": self.success,
                "patch_files_dir": self.patch_files_dir,
                "repo_invariant_scores": self.repo_invariant_scores,
                "bounty_invariant_scores": self.bounty_invariant_scores,
            }
        )
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> "PatchAgentMessage":
        """Reconstruct a patch agent message from its dictionary representation"""
        agent_id = data.get("agent_id")
        message = data.get("message", "")
        success = data.get("success", False)
        patch_files_dir = data.get("patch_files_dir")

        agent_message = cls(
            agent_id=agent_id,
            message=message,
            success=success,
            patch_files_dir=patch_files_dir,
        )

        # Set base Message properties
        agent_message._id = data.get("current_id")
        agent_message.timestamp = data.get("timestamp")

        # Handle prev/next relationships
        if "prev" in data:
            agent_message._prev = data.get("prev")
        if "next" in data:
            agent_message._next = data.get("next")

        # Set specialized fields
        agent_message._repo_invariant_scores = data.get("repo_invariant_scores", {})
        agent_message._bounty_invariant_scores = data.get("bounty_invariant_scores", {})

        return agent_message
