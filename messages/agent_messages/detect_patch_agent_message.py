from messages.agent_messages.agent_message import AgentMessage


class DetectPatchAgentMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: str = None,
        success: bool = False,
        patch_files_dir: str = None,
        submission: bool = False,
        prev: AgentMessage = None,
    ) -> None:
        super().__init__(agent_id=agent_id, message=message, prev=prev)
        self._success = success
        self._patch_files_dir = patch_files_dir
        self._submission = submission

    @property
    def success(self) -> bool:
        return self._success

    def set_success(self, value: bool):
        self._success = value

    @property
    def submission(self) -> bool:
        return self._submission

    def set_submission(self, value: bool):
        self._submission = value

    @property
    def patch_files_dir(self) -> str:
        return self._patch_files_dir

    def set_patch_files_path(self, value: str):
        self._patch_files_dir = value

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        base_dict.update(
            {
                "success": self.success,
                "patch_files_dir": self.patch_files_dir,
                "submission": self.submission,
            }
        )
        return base_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        base_dict.update(
            {
                "success": self.success,
                "patch_files_dir": self.patch_files_dir,
                "submission": self.submission,
            }
        )
        return base_dict
