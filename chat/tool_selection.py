"""Küçük modellere yalnız açıkça gereken araçları gösterir."""


_SELAM = (
    "merhaba", "selam", "günaydın", "gunaydin", "iyi akşamlar",
    "iyi aksamlar", "nasılsın", "nasilsin", "naber",
)
_LISTELE = (
    "neler var", "ne var", "hangi dosyalar", "listele", "klasörler",
    "klasorler", "masaüstü", "masaustu", "belgelerim", "indirilenler",
)
_DOSYA_OKU = (
    "dosyayı oku", "dosyayi oku", "dosya içeriği", "dosya icerigi",
    "içinde ne yazıyor", "icinde ne yaziyor", "bu dosyayı aç",
    "bu dosyayi ac",
)


def _yalniz(tools, ad):
    return [t for t in (tools or [])
            if t.get("function", {}).get("name") == ad]


def select_tools(text, tools, small_model=False, fallback=None):
    """Açık istekleri daraltır; belirsiz isteklerde eski seçimi korur."""
    mevcut = list(tools or [])
    if not mevcut:
        return []
    if not small_model:
        return list(fallback if fallback is not None else mevcut)

    t = (text or "").strip().lower()
    if any(k in t for k in _SELAM) and not any(k in t for k in _LISTELE):
        return []
    if any(k in t for k in _DOSYA_OKU):
        return _yalniz(mevcut, "read_file")
    if any(k in t for k in _LISTELE):
        return _yalniz(mevcut, "list_files")
    return list(fallback if fallback is not None else mevcut)