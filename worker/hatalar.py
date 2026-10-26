"""İşçi hata türleri — ağır bağımlılık taşımayan ortak modül.

`worker.tarayici` Playwright ister. İşçi çalıştırıcısı ve testleri ise
tarayıcı olmadan da bu hata türünü tanıyabilmeli; bu yüzden sınıf burada
durur, `worker.tarayici` onu yeniden dışa verir.
"""


class TarayiciHatasi(RuntimeError):
    """Tarayıcı adımı güvenli biçimde tamamlanamadı."""
