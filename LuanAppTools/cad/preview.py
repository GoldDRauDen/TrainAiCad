"""Render saved DXF geometry with ezdxf's drawing backend (including real arcs)."""

from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing.svg import SVGBackend


def render_dxf(path: Path, destination: Path) -> Path:
    document = ezdxf.readfile(path)
    if document.audit().has_errors:
        raise ValueError("Cannot preview invalid DXF")
    backend = SVGBackend()
    Frontend(RenderContext(document), backend).draw_layout(
        document.modelspace(), finalize=True
    )
    svg = backend.get_string(layout.Page(0, 0))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8")
    return destination
