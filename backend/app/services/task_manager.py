from app.models.schemas import TaskStatus, AnalysisResult


class TaskManager:
    """In-memory task manager for tracking async background tasks."""

    def __init__(self):
        self._tasks: dict[str, TaskStatus] = {}

    def create_task(self, task_id: str, message: str = "") -> TaskStatus:
        task = TaskStatus(task_id=task_id, status="pending", message=message)
        self._tasks[task_id] = task
        return task

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: AnalysisResult | None = None,
    ) -> TaskStatus | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if result is not None:
            task.result = result
        return task

    def get_task(self, task_id: str) -> TaskStatus | None:
        return self._tasks.get(task_id)

    def delete_task(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None


task_manager = TaskManager()
