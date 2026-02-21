import html

from app.services.shell import ExecResult


def clip_text(text: str, limit: int = 3200) -> str:
    clean = text.strip()
    if not clean:
        return "(пусто)"
    if len(clean) <= limit:
        return clean
    return clean[: limit - 24] + "\n... вывод обрезан ..."


def pre(text: str, limit: int = 3200) -> str:
    return f"<pre>{html.escape(clip_text(text, limit=limit))}</pre>"


def command_report(title: str, result: ExecResult, limit: int = 3000) -> str:
    status = "TIMEOUT" if result.timed_out else str(result.returncode)
    payload = result.stdout.strip()
    err = result.stderr.strip()
    if err:
        if payload:
            payload = f"{payload}\n\nstderr:\n{err}"
        else:
            payload = f"stderr:\n{err}"
    if not payload:
        payload = "(пусто)"
    clipped = clip_text(payload, limit=limit)
    return (
        f"<b>{html.escape(title)}</b>\n"
        f"<code>{html.escape(result.command)}</code>\n"
        f"<b>Код:</b> {html.escape(status)} | <b>Время:</b> {result.duration:.2f} c\n"
        f"<pre>{html.escape(clipped)}</pre>"
    )
