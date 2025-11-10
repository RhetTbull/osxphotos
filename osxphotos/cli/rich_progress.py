"""rich Progress bar factory that can return a rich Progress bar or a mock Progress bar"""

import os
from typing import Any, Optional, Union

from rich.console import Console
from rich.progress import GetTimeCallable, Progress, ProgressColumn, TaskID

# set to 1 if running tests
OSXPHOTOS_IS_TESTING = bool(os.getenv("OSXPHOTOS_IS_TESTING", default=False))


class MockTask:
    """A mock task object similar to rich.progress.Task."""
    def __init__(self, task_id, description="", total=100):
        self.id = task_id
        self.description = description
        self.total = total
        self.completed = 0
        self.finished = False


class MockProgress:
    """A mock version of rich.Progress for testing purposes."""
    def __init__(self, *args, **kwargs):
        self.tasks = []
        self.live = False
        self.console = kwargs.get("console", None)
        self.auto_refresh = kwargs.get("auto_refresh", True)
        self.transient = kwargs.get("transient", False)

    # --- Context manager methods ---
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # --- Lifecycle methods ---
    def start(self):
        self.live = True

    def stop(self):
        self.live = False

    def refresh(self):
        pass  # dummy method, does nothing

    # --- Task management ---
    def add_task(self, description="", total=100, **kwargs):
        task_id = len(self.tasks)
        task = MockTask(task_id, description, total)
        self.tasks.append(task)
        return task_id

    def update(self, task_id, advance=0, completed=None, total=None, **kwargs):
        task = self.tasks[task_id]
        if completed is not None:
            task.completed = completed
        if total is not None:
            task.total = total
        if advance:
            task.advance(advance)
        return task

    def advance(self, task_id: TaskID, advance: float = 1) -> None:
        pass
        # task = self.tasks[task_id]
        # task.advance(advance)

    def remove_task(self, task_id):
        self.tasks[task_id] = None  # keep index stable

    def get_task(self, task_id):
        return self.tasks[task_id]

    # --- Output simulation ---
    def print(self, *args, **kwargs):
        # mimic console.print()
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)

    # --- Misc / dummy API methods ---
    def __getitem__(self, task_id):
        return self.tasks[task_id]

    def __len__(self):
        return len(self.tasks)

    def reset(self, task_id, total=None):
        task = self.tasks[task_id]
        task.completed = 0
        if total is not None:
            task.total = total
        task.finished = False

    def stop_task(self, task_id):
        task = self.tasks[task_id]
        task.finished = True


def rich_progress(
    *columns: Union[str, ProgressColumn],
    console: Optional[Console] = None,
    auto_refresh: bool = True,
    refresh_per_second: float = 10,
    speed_estimate_period: float = 30.0,
    transient: bool = False,
    redirect_stdout: bool = True,
    redirect_stderr: bool = True,
    get_time: Optional[GetTimeCallable] = None,
    disable: bool = False,
    expand: bool = False,
    mock: bool = False,
) -> Progress | MockProgress:
    """Return a rich.progress.Progress object unless mock=True or os.getenv("OSXPHOTOS_IS_TESTING") is set"""
    # if OSXPHOTOS_IS_TESTING is set or mock=True, return a MockProgress object
    if mock or OSXPHOTOS_IS_TESTING:
        return MockProgress()
    return Progress(
        *columns,
        console=console,
        auto_refresh=auto_refresh,
        refresh_per_second=refresh_per_second,
        speed_estimate_period=speed_estimate_period,
        transient=transient,
        redirect_stdout=redirect_stdout,
        redirect_stderr=redirect_stderr,
        get_time=get_time,
        disable=disable,
        expand=expand,
    )
