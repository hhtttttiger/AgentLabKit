from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from application.execution.run_projection import RunReader


def get_run_reader(request: Request) -> RunReader:
    reader = getattr(request.app.state, "run_reader", None)
    if reader is None:
        raise RuntimeError("RunReader not initialized — check lifespan wiring")
    return reader


RunReaderDep = Annotated[RunReader, Depends(get_run_reader)]
