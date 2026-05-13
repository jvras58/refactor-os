"""Dashboard controller for dashboard endpoints."""
from __future__ import annotations

import jinja2
from fastapi import Request
from fastapi.responses import HTMLResponse


async def render_dashboard(request: Request):
    """
    Renderiza o dashboard de sandbox usando Jinja2.
    """
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("app/templates"), cache_size=0)
    template = env.get_template("dashboard.html")
    html_content = template.render(
        request=request,
        title="RefactorOS Sandbox"
    )
    return HTMLResponse(content=html_content)