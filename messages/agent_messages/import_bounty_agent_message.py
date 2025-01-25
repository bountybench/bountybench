from typing import Any, Dict
from messages.agent_messages.agent_message import AgentMessage

class ImportBountyMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: str,
        success: str,
        bounty_link: str,
        cwe: str,
        cve: str,
        severity: str,
        disclosure_bounty: str,
        patch_bounty: str,
        detect_prompt_some_info: str,
        detect_prompt_less_info: str,
        exploit_prompt: str,
        patch: dict,
        vulnerable_commit: str,
        prev: AgentMessage = None,
    ) -> None:
        self._success = success
        self._bounty_link = bounty_link
        self._CWE = cwe
        self._CVE = cve
        self._severity = severity
        self._disclosure_bounty = disclosure_bounty
        self._patch_bounty = patch_bounty
        self._detect_prompt_some_info = detect_prompt_some_info
        self._detect_prompt_less_info = detect_prompt_less_info
        self._exploit_prompt = exploit_prompt
        self._patch = patch
        self._vulnerable_commit = vulnerable_commit
        super().__init__(agent_id, message, prev)

    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def bounty_link(self) -> str:
        return self._bounty_link

    @property
    def cwe(self) -> str:
        return self._CWE

    @property
    def cve(self) -> str:
        return self._CVE

    @property
    def severity(self) -> str:
        return self._severity

    @property
    def disclosure_bounty(self) -> str:
        return self._disclosure_bounty

    @property
    def patch_bounty(self) -> str:
        return self._patch_bounty

    @property
    def detect_prompt_some_info(self) -> str:
        return self._detect_prompt_some_info

    @property
    def detect_prompt_less_info(self) -> str:
        return self._detect_prompt_less_info

    @property
    def exploit_prompt(self) -> str:
        return self._exploit_prompt

    @property
    def patch(self) -> str:
        return self._patch

    @property
    def vulnerable_commit(self) -> str:
        return self._vulnerable_commit
    
    def to_dict(self) -> Dict[str, Any]:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "bounty_link": self._bounty_link,
            "CWE": self._CWE,
            "CVE": self._CVE,
            "severity": self._severity,
            "disclosure_bounty": self._disclosure_bounty,
            "patch_bounty": self._patch_bounty,
            "detect_prompt_some_info": self._detect_prompt_some_info,
            "detect_prompt_less_info": self._detect_prompt_less_info,
            "exploit_prompt": self._exploit_prompt,
            "patch": self._patch,
            "vulnerable_commit": self._vulnerable_commit
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict