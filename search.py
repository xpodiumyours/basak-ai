"""search.py — DuckDuckGo ile ücretsiz web araması.
API anahtarı gerektirmez. Sonuçları kısa özet olarak döndürür."""

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


def web_ara(soru, sonuc_sayisi=3):
    """DuckDuckGo'da arama yapar, kısa sonuç listesi döndürür.
    
    Args:
        soru: Arama sorgusu
        sonuc_sayisi: Kaç sonuç döndürüleceği (varsayılan 3)
    
    Returns:
        dict: {"ok": True, "sonuclar": [...]} veya {"ok": False, "hata": "..."}
    """
    if DDGS is None:
        return {"ok": False, "hata": "duckduckgo-search yüklü değil"}
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(soru, region="tr-tr", max_results=sonuc_sayisi))
        
        if not results:
            return {"ok": True, "sonuclar": [], "mesaj": "Sonuç bulunamadı"}
        
        sonuclar = []
        for r in results:
            sonuclar.append({
                "baslik": r.get("title", ""),
                "url": r.get("href", ""),
                "ozet": r.get("body", "")[:200],  # Kısa özet
            })
        
        return {"ok": True, "sonuclar": sonuclar}
    
    except Exception as e:
        return {"ok": False, "hata": str(e)}


def arama_baglam_olustur(soru, sonuc_sayisi=3):
    """Arama sonuçlarını model için bağlam metnine dönüştürür.
    
    Returns:
        str: Modelin kullanabileceği bağlam metni veya boş string.
    """
    sonuc = web_ara(soru, sonuc_sayisi)
    
    if not sonuc.get("ok") or not sonuc.get("sonuclar"):
        return ""
    
    parcalar = ["İnternetten bulunan bilgiler:"]
    for i, s in enumerate(sonuc["sonuclar"], 1):
        parcalar.append(f"{i}. {s['baslik']}")
        parcalar.append(f"   {s['ozet']}")
        parcalar.append(f"   Kaynak: {s['url']}")
    
    return "\n".join(parcalar)
