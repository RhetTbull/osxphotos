"""rich Progress bar factory that can return a rich Progress bar or a mock Progress bar"""

import os
from typing import Any, Optional, Union

from rich.console import Console
from rich.progress import GetTimeCallable, Progress, ProgressColumn, TaskID

# set to 1 if running tests
OSXPHOTOS_IS_TESTING = bool(os.getenv("OSXPHOTOS_IS_TESTING", default=False))


class MockProgress:
    def __init__(self):
        pass

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: float = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        pass

    def advance(self, task_id: TaskID, advance: float = 1) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


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
) -> None:
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
