import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.definitions import TOOLS
from chat.agent_protocol import YETENEK_ALANLARI

out = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "basak_gateway/generated/tool_schemas.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "generated_from": "tools.definitions.TOOLS",
    "total": len(TOOLS),
    "areas": {k: list(v) for k, v in YETENEK_ALANLARI.items()},
    "tools": TOOLS,
}
out.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(out)
