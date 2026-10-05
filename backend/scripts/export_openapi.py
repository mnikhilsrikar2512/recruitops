"""Write the API's OpenAPI document (used by the frontend contract tests).

    cd backend && python scripts/export_openapi.py ../frontend/tests/openapi.json

Needs the backend's Python dependencies but no database: the schema is built
from the routers and pydantic models only.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
target.write_text(json.dumps(app.openapi(), indent=1, sort_keys=True, default=str))
print(f"wrote {target} ({len(app.openapi()['paths'])} paths)")
