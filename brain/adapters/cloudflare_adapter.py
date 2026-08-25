"""brain/adapters/cloudflare_adapter — Cloudflare Workers AI provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _CloudflareAdapter:
    @property
    def name(self):
        return "cloudflare"

    def create(self, ayar):
        from brain.cloudflare import CloudflareClient
        account = (os.environ.get("CLOUDFLARE_ACCOUNT_ID")
                   or ayar.get("cloudflare_account_id") or "")
        key = (os.environ.get("CLOUDFLARE_API_TOKEN")
               or ayar.get("cloudflare_api_token") or "")
        if not account or not key:
            return None
        try:
            return CloudflareClient(account, key)
        except ValueError as e:
            logger.warning("Cloudflare başlatılamadı: %s", e)
            return None


adapter = _CloudflareAdapter()
