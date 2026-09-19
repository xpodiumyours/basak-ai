import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.definitions import TOOLS, TANINMIS_TOOLLAR
from chat.agent_protocol import YETENEK_ALANLARI

catalog = json.loads((ROOT / "basak_gateway/src/tool_catalog.json").read_text(encoding="utf-8"))
schemas = json.loads((ROOT / "basak_gateway/src/tool_schemas.json").read_text(encoding="utf-8"))
actual_names = [t["function"]["name"] for t in TOOLS]
catalog_areas = catalog["areas"]
catalog_names = [name for names in catalog_areas.values() for name in names]

assert len(TOOLS) == 52, len(TOOLS)
assert len(TANINMIS_TOOLLAR) == 52, len(TANINMIS_TOOLLAR)
assert catalog["total"] == 52
assert len(catalog_names) == 52
assert len(set(catalog_names)) == 52
assert set(catalog_names) == set(actual_names)
assert {k: tuple(v) for k, v in catalog_areas.items()} == dict(YETENEK_ALANLARI)
assert schemas["total"] == 52
assert schemas["tools"] == TOOLS
assert {k: tuple(v) for k, v in schemas["areas"].items()} == dict(YETENEK_ALANLARI)
print("gateway catalog+schemas: 52/52 tools, 10/10 areas, exact source parity OK")
