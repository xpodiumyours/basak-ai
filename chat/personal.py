"""Her konuşma yolunun kullandığı kişisel tur hazırlığı."""

from dataclasses import dataclass, field
import logging
import re

logger = logging.getLogger(__name__)

_KIMLIK_SORULARI = frozenset((
    "sen kimsin", "kimsin", "sen nesin", "nesin",
    "senin adın ne", "senin adin ne", "adın ne", "adin ne",
    "senin adın nedir", "senin adin nedir", "adın nedir", "adin nedir",
))


@dataclass
class PreparedPersonalTurn:
    text: str
    speaker: str = ""
    profile_block: str = ""
    learning_note: str = ""
    recent_history: list = field(default_factory=list)


def _speaker_and_text(text):
    temiz = (text or "").strip()
    eslesme = re.search(r"\[([^\]]+)\]\s*$", temiz)
    if not eslesme:
        return temiz, ""
    return temiz[:eslesme.start()].strip(), eslesme.group(1).strip()


def deterministic_reply(text):
    """Modelden bağımsız olması gereken dar kişisel cevaplar."""
    temiz = (text or "").strip().rstrip("?!.… ").lower()
    if temiz in _KIMLIK_SORULARI:
        return "Ben Başak'ım, Casper'ın kişisel asistanıyım."
    return ""


def prepare_personal_turn(text, motor=None, history=None):
    """Metni, kalıcı profili ve yakın geçmişi tek pakette hazırlar."""
    temiz, speaker = _speaker_and_text(text)
    profil_blogu = ""
    ogrenme_notu = ""

    if motor and temiz:
        try:
            from memory.profil import blok, ogren, unut

            silinen = unut(motor, temiz)
            if silinen == -1:
                ogrenme_notu = (
                    "Not: Casper hakkındaki tüm profil bilgilerini SİLDİN. "
                    "Bunu kısaca doğrula."
                )
            elif silinen:
                ogrenme_notu = (
                    "Not: profilden %d kayıt sildin (istek: %s). "
                    "Bunu kısaca doğrula." % (silinen, temiz)
                )
            else:
                yeniler = ogren(motor, temiz, speaker=speaker)
                if yeniler:
                    ogrenme_notu = (
                        "Not: profile yeni bilgi eklendi: %s. "
                        "Kısaca doğrulayıp sohbete devam et."
                        % "; ".join("%s=%s" % (alan, deger)
                                    for alan, deger in yeniler)
                    )
            profil_blogu = blok(motor)
        except Exception as exc:
            logger.warning("Kisisel tur hazirlanamadi: %s", exc)

    return PreparedPersonalTurn(
        text=temiz,
        speaker=speaker,
        profile_block=profil_blogu,
        learning_note=ogrenme_notu,
        recent_history=list(history or []),
    )