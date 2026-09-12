"""tools — Internet araclari (yalniz iki tane, ikisi de salt-okunur).

2026-09-13: 21 araclik katman sokuldu; Casper "internet kalsin" dedi.
Yazma, sistem, dosya araci YOK — bu paket disariya yalniz okur.
"""

import logging

from tools.definitions import TOOLS, TANINMIS_TOOLLAR  # noqa: F401

logger = logging.getLogger(__name__)


def calistir(tool_name, args):
    """Araci calistirir. Beyaz liste disi ad ASLA kosmaz.

    Donus: dict — {"result": ...} veya {"error": ...}
    """
    if tool_name not in TANINMIS_TOOLLAR:
        logger.info("Taninmayan arac reddedildi: %s", tool_name)
        return {"error": "'%s' diye bir arac yok." % tool_name}

    from tools import web_search as _ws
    try:
        if tool_name == "web_search":
            return _ws.web_search(str((args or {}).get("query", "")))
        if tool_name == "sayfa_oku":
            return _ws.sayfa_oku(str((args or {}).get("url", "")))
    except Exception as e:
        logger.warning("Arac hatasi (%s): %s", tool_name, e)
        return {"error": "Arac calismadi: %s" % str(e)[:150]}
    return {"error": "'%s' calistirilamadi." % tool_name}
