import asyncio
import shlex
import time
from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class ExecResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool


async def run_exec(command: Sequence[str], timeout: int) -> ExecResult:
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True
    duration = time.monotonic() - started
    return ExecResult(
        command=shlex.join(command),
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        duration=duration,
        timed_out=timed_out,
    )


async def run_shell(command: str, timeout: int) -> ExecResult:
    started = time.monotonic()
    process = await asyncio.create_subprocess_shell(
        command,
        executable="/bin/bash",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True
    duration = time.monotonic() - started
    return ExecResult(
        command=command,
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        duration=duration,
        timed_out=timed_out,
    )
