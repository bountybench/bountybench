from contextvars import ContextVar

current_workflow_id = ContextVar("current_workflow_id", default=None)
current_phase_id = ContextVar("current_phase_id", default=None)


class ContextManager:
    def __init__(self, context_var: ContextVar, value: str):
        self.context_var = context_var
        self.value = value
        self._token = None

    def __enter__(self):
        self._token = self.context_var.set(self.value)
        return self

    def __exit__(self, *args):
        self.context_var.reset(self._token)


class WorkflowContext(ContextManager):
    def __init__(self, workflow_id: str):
        super().__init__(current_workflow_id, workflow_id)


class PhaseContext(ContextManager):
    def __init__(self, phase_id: str):
        super().__init__(current_phase_id, phase_id)
