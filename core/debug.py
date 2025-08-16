from typing import Optional, List

try:
    from rich.console import Console
    from rich.panel import Panel
    _console: Optional[Console] = Console()
except Exception:
    _console = None
    Panel = None  # type: ignore


_LOG_BUFFER: List[str] = []


def debug_log(enabled: bool, title: str, body: str) -> None:
    # Suppress raw prompts from both console and file
    if "Prompt" in title:
        return
    formatted = f"=== {title} ===\n{body}\n=== end {title} ==="
    _LOG_BUFFER.append(formatted)
    if not enabled:
        return
    if _console and Panel:
        _console.print(Panel.fit(body, title=title))
    else:
        print(formatted)


def get_logs_text() -> str:
    return "\n\n".join(_LOG_BUFFER)
