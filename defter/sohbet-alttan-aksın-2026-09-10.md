---
kim:    opencode
tarih:  2026-09-10
konu:   basak
tip:    karar
omur:   sonsuz
kaynak: Casper ekran goruntusu + ui/style.css + node --check
---

Casper: mesajlar ustten basliyor, alttan yukari gitsin. Sebep: .messages sutunu kaydirma alaninin ustune yapisikti, az mesajda bosluk altta kaliyordu. Cozum (mevcut renk/olcu degiskenlerine dokunmadan): .chat-scroll esnek sutun oldu, .messages margin-top:auto ile dibe sabitlendi; cok mesajda kaydirma ve otomatik dibe inme aynen calisir. Dogrulama: CSS parantez dengesi + node --check temiz; uygulama yeniden baslatildi.
