"""User info memory - what ShopAI remembers about a shopper between sessions.

Backed by the `user_memory` table in Supabase, one row per user. Every call
carries the caller's access token, so Postgres sees `auth.uid()` and row level
security confines each user to their own row. The server holds no privileged
key: without a token there is no access, which is the point.
"""

import base64
import json
import os
from typing import Any, Optional

from supabase import Client, create_client

from shopai.memory.base import Memory

# Columns the caller may set. Anything else belongs in `details`.
TEXT_FIELDS = (
    "culture_summary", "height", "body_type",
    # Colour tone
    "skin_tone", "undertone", "color_season", "contrast_level",
)
LIST_FIELDS = (
    "colors_that_work", "colors_to_avoid",
    "preferred_fabrics", "preferred_pieces", "preferred_styles",
)
WRITABLE_FIELDS = TEXT_FIELDS + LIST_FIELDS + ("details",)

TABLE = "user_memory"


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


def _supabase_key() -> str:
    return os.environ.get("SUPABASE_ANON_KEY", "")


def user_id_from_token(access_token: str) -> str:
    """Read the subject out of a Supabase JWT.

    The signature is not checked here on purpose - Postgres verifies the token
    and enforces RLS. This only saves the caller from passing the id twice, so
    a forged `sub` buys nothing: the database still refuses the row.
    """
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("sub", "")
    except Exception:
        return ""


class UserInfoMemory(Memory):
    """Persistent styling profile for one user.

    Stored fields:
        culture_summary    what their context and culture mean for dressing
        height             as they describe it
        body_type          curvy, wavy, oval, ...
        skin_tone          fair, light, medium, olive, deep
        undertone          warm, cool, neutral
        color_season       spring, summer, autumn, winter
        contrast_level     high, medium, low - how much contrast suits them
        colors_that_work   colours that suit them
        colors_to_avoid    colours that fight their tone
        preferred_fabrics  fabrics they like wearing
        preferred_pieces   outfit pieces they reach for
        preferred_styles   the styles they lean towards
        details            anything not worth its own column yet (jsonb)
    """

    name = "user_info"

    def _client(self, access_token: str) -> Client:
        """A client acting as the user, not as the service.

        Raises:
            RuntimeError: if Supabase is unconfigured or no token was given -
                both would otherwise fail later and less clearly.
        """
        url, key = _supabase_url(), _supabase_key()
        if not url or not key:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
            )
        if not access_token:
            raise RuntimeError("An access token is required: user memory is per-user.")

        client = create_client(url, key)
        client.postgrest.auth(access_token)
        return client

    # ------------------------------------------------------------------ read

    def read(self, key: str = "", *, access_token: str = "", **_: Any) -> dict:
        """Return the stored row, or {} when the user has no memory yet.

        Args:
            key: the user id. Taken from the token when omitted.
            access_token: the caller's Supabase access token.
        """
        user_id = key or user_id_from_token(access_token)
        if not user_id:
            return {}

        client = self._client(access_token)
        result = (
            client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else {}

    # ----------------------------------------------------------------- write

    def write(self, key: str = "", values: Optional[dict] = None, *,
              access_token: str = "", **_: Any) -> dict:
        """Upsert what we know about a user and return the stored row.

        Only the columns present in `values` are sent, so a partial write
        leaves the rest of the row alone. Unknown keys are folded into
        `details` rather than dropped, since losing what an agent learned is
        worse than storing it loosely.
        """
        user_id = key or user_id_from_token(access_token)
        if not user_id:
            raise ValueError("No user id: pass one, or a token that carries a subject.")

        values = values or {}
        row: dict[str, Any] = {"user_id": user_id}
        extras: dict[str, Any] = {}

        for field, value in values.items():
            if field in WRITABLE_FIELDS:
                row[field] = value
            else:
                extras[field] = value

        if extras:
            row["details"] = {**(row.get("details") or {}), **extras}

        client = self._client(access_token)
        result = (
            client.table(TABLE)
            .upsert(row, on_conflict="user_id")
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_details(self, key: str = "", details: Optional[dict] = None, *,
                       access_token: str = "") -> dict:
        """Merge keys into `details` without disturbing the typed columns."""
        current = self.read(key, access_token=access_token).get("details") or {}
        return self.write(key, {"details": {**current, **(details or {})}},
                          access_token=access_token)

    # ---------------------------------------------------------------- delete

    def delete(self, key: str = "", *, access_token: str = "", **_: Any) -> bool:
        """Forget a user entirely. True when a row was actually removed."""
        user_id = key or user_id_from_token(access_token)
        if not user_id:
            return False

        client = self._client(access_token)
        result = client.table(TABLE).delete().eq("user_id", user_id).execute()
        return bool(result.data)
