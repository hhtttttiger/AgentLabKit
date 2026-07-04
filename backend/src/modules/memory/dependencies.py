"""长期记忆依赖注入。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from memory import MemoryModule


def get_memory_module(request: Request) -> MemoryModule:
    mod: MemoryModule | None = getattr(request.app.state, "memory_module", None)
    if mod is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory module is not enabled — set LONG_TERM_MEMORY_ENABLED=true",
        )
    return mod


MemoryModuleDep = Annotated[MemoryModule, Depends(get_memory_module)]
