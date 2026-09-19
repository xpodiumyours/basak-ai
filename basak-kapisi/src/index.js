// basak-kapisi/src/index.js — TEK GOREV: kalici adresi canli Basak
// web ekranina yonlendirmek. Beyin YOK (AGENTS.md §9): bu dosyada
// ajan dongusu, saglayici, arac katalogu, sahte kabul mantigi YOKTUR
// (hepsi 2026-09-20'de Cloudflare dash'tan silindi; gecmis arsiv
// etiketlerinde durur: arsiv/feature-basak-web-gate-2-20260919).
//
// NOT: Hedef adres trycloudflare gecici tunel adresidir; tunel her
// yeniden acildiginda bu satir guncellenir. Kalici cozum (alan adi
// ekleme veya Workers'un kopruye dogrudan proxy'si) plan dosyasinda:
// knowledge/web-kopru-plani.md "Kalicilik" bolumu.
export default {
  async fetch() {
    return Response.redirect(
      "https://laptop-lawyer-blend-periodic.trycloudflare.com/", 302);
  },
};
