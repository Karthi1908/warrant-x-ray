"""Export FastAPI OpenAPI schema to openapi.json at the repository root."""

from __future__ import annotations

import json
from pathlib import Path
from warrantx.api.app import create_app


def export_openapi(output_path: Path = Path("openapi.json")) -> None:
    """Generate and write OpenAPI JSON document."""
    app = create_app()
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {output_path.resolve()}")


if __name__ == "__main__":
    export_openapi()
