# AGENTS.md — Başak Ajan Kuralları

Bu dosyayı kod yazan her ajan (Claude Code, Kilo Code, OpenCode) işe başlamadan önce okur. Kurallar bağlayıcıdır. Casper kod yazmıyor, doğal dille tarif ediyor — tarifi karara çevirmek ajanın işi, "anlamadım" diye boş bırakmak değil.

## 0. Proje

Başak — tamamen yerel çalışan, ücretsiz, Türkçe konuşan kişisel Jarvis. Beyin: Ollama (`qwen2.5:3b`, yerel) + zor sorularda Groq'a (ücretsiz, `llama-3.3-70b`) kaçış. Ses: Piper TTS + faster-whisper STT (ikisi de yerel). Arayüz: `ui/` altında saf HTML/CSS/JS + Three.js orb, pywebview masaüstü penceresinde açılıyor. `ARASTIRMA.md` teknoloji seçim gerekçelerini tutar.

**19 Ağustos 2026'da başladı, tek günlük iş.** `git` bugün kuruldu — öncesinde hiç versiyon geçmişi yoktu, ilk commit'ten öncesi kurtarılamaz.

## 1. Kilitli hedef

Kişisel, tamamen yerel/ücretsiz çalışan bir Jarvis: sesli + yazılı konuşabilen, Casper'ı tanıyan, **kendi notlarını (`knowledge/`) okuyup kullanabilen**, bilgisayarda arka planda güvenilir çalışan bir asistan. Bulut (Groq) sadece yerel model yetmediğinde devrede — sürekli internet/abonelik bağımlılığı hedef değil.

## 1.1. Sonraki özellikler

`GOREV_LISTESI.md`'de 5 adet onaylı yön var (gerçek hafıza sistemi, bilgisayarda iş yapma, güncel bilgi/web arama, görev takibi, yeni güven sınırı). Kilitli sıra yok — hangisi açılırsa buraya "şu an neredeyiz" olarak işlenir.

## 2. Şu an neredeyiz / sıra

1. **Çalışıyor:** sohbet (Ollama), TTS açma/kapama, sesli dinleme (STT), model seçimi, geçmiş (`gecmis.json`), 3D orb durum göstergesi (bekliyor/düşünüyor/cevaplıyor/hata/dinliyor — `ui/app.js`).
2. **Eksik — sıradaki iş:** `knowledge/` klasörü (`damla-sulama.md`, `toprak-nemi-sensorleri.md` gibi Casper'ın kendi notları) **hiçbir cevaba karışmıyor**. `Api.knowledge()` sadece dosya adlarını UI'a listeliyor, `_chat()` içinde okunmuyor. Jarvis hissi için asıl kilit nokta bu — kendi bilgisini kullanmayan asistan sadece bir chatbot.
3. Bunun ötesi (otomatik başlatma, sistem tepsisi, başka entegrasyonlar) — Casper istemeden ajan kendi kafasına göre eklemez. Kapsamı o büyütür.

## 3. Doğal dil çevirme kuralı

Casper "sesi daha insansı yap", "beni tanısın", "notlarımı kullansın" gibi belirsiz bir istek söylediğinde:
1. Önce ilgili dosyayı oku (`voice.py`, `basak_app.py`'deki `KISILIK`, `knowledge/`) — mevcut yapıyı anla.
2. İsteği somut bir değişikliğe çevir (hangi fonksiyon, hangi parametre, hangi prompt satırı).
3. Belirsizse Casper'a **teknik terimsiz** kısa bir soru sor — "anlamadım" deyip beklemek veya rastgele bir şey uydurmak yasak.

## 4. Tasarım kuralı — zorunlu

Her UI görevinde: önce **`ui-ux-pro-max`** skill'ini oku, sonra `ui/style.css`'teki mevcut `:root` değişkenlerini (renkler, `--radius`, `--font`) kaynak kimlik olarak kullan — yeni palet icat etme. "Modern yap" gibi sözleri önce somut karara (renk/tipografi/spacing/motion) dök, sonra kodla.

## 5. Vibe coding yasakları

- **Kanıtsız "çalışıyor" deme.** Değişiklikten sonra uygulamayı gerçekten çalıştır (`python basak_app.py` veya `basak.cmd`), konsol çıktısını/ekran görüntüsünü göster. Otomatik test yok — bu yüzden gerçek çalıştırma tek kanıt.
- **Dosyayı düzenle, yeniden yazma.** Küçük bir düzeltme için `basak_app.py`/`brain.py`/`voice.py`'yi baştan üretme.
- **Sır asla commit'e girmez.** `GROQ_API_KEY`, `ayarlar.json`, `gecmis.json` — hepsi `.gitignore`'da, öyle kalacak. Pre-commit hook bunu da kontrol ediyor (§6).
- **Var olmayan paket kurma.** Yeni bir pip paketi eklemeden önce gerçekten var olduğunu doğrula (`pip show`/PyPI).
- **Hata yollarını es geçme.** Ollama kapalıysa, mikrofon yoksa, Groq anahtarı geçersizse — kullanıcıya anlamlı bir mesaj dönsün (mevcut kod bunu zaten yapıyor, bu standardı düşürme).

## 6. Doğrulama

Proje küçük, otomatik test suite'i yok — bu yüzden minimum kapı:

| Kapı | Komut | Ne zaman |
|---|---|---|
| Python sözdizimi | `python -m py_compile <dosya>` | Her `.py` değişikliğinde — **pre-commit hook zaten zorunlu kılıyor** |
| Gerçek çalıştırma | `python basak_app.py` aç, özelliği elle dene | Her görev sonunda, "bitti" demeden önce |
| Sır sızıntı kontrolü | commit'e `ayarlar.json`/`gecmis.json` girmemiş | Pre-commit hook otomatik engelliyor |

`git commit --no-verify` ile bu kapıyı atlamak, hatayı görünmez kılar — kullanma.

## 7. Bu dosya

Casper ile konuşulmadan kapsamı büyütülmez (örn. "şimdi CI kuralım", "test suite yazalım" gibi ağır adımlar — proje buna henüz hazır değil, gerekirse ayrıca konuşulur).
