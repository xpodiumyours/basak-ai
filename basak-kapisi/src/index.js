// basak-kapisi/src/index.js — TEK GOREV: kalici adresi canli Basak
// web ekranina yonlendirmek. Beyin YOK (AGENTS.md §9): bu dosyada
// ajan dongusu, saglayici, arac katalogu, sahte kabul mantigi YOKTUR
// (hepsi 2026-09-20'de Cloudflare dash'tan silindi; gecmis arsiv
// etiketlerinde durur: arsiv/feature-basak-web-gate-2-20260919).
//
// HEDEF: tunel adresi ARTIK kodda sabit degil — KV'de "url" anahtarinda
// tutulur (resmi KV ucretsiz limiti: 100.000 okuma/gun, 1.000 yazma/gun;
// bizim kullanim gunluk birkac yazma). Nobetci (basak-nobetci.ps1) yeni
// trycloudflare adresini KV'ye yazar; kod duzenleme + deploy kalkar.
export default {
  async fetch(request, env) {
    const hedef = await env.HEDEF.get("url");
    if (!hedef) {
      return new Response(
        "Basak kapisinin tunel adresi kayitli degil. Nobetci yazinca " +
        "bu adres acilir. (HEDEF KV'sinde 'url' anahtari bos)",
        { status: 503 });
    }
    return Response.redirect(hedef, 302);
  },
};
