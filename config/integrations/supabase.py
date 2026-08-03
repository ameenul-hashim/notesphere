"""
Supabase integration - PLACEHOLDER. NOT CONNECTED YET.

Supabase will provide Auth, PostgreSQL (via Neon or Supabase's own Postgres),
Storage, and Realtime. Planned activation steps:

    1. Create a Supabase project and copy its project URL and keys.
    2. Add the following to `.env`:
           SUPABASE_URL=https://<project-ref>.supabase.co
           SUPABASE_ANON_KEY=<anon-key>
           SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
           SUPABASE_JWT_SECRET=<jwt-secret>
    3. Install the official client when wiring begins, e.g.:
           pip install supabase
    4. Build the client lazily here (never at import time) and consume it
       from the accounts / community apps.

This module currently ships no live code on purpose.
"""

import os


class SupabaseClient:
    """Lazy placeholder for the Supabase client. Not wired into the app yet."""

    def __init__(self) -> None:
        self.url = os.environ.get("SUPABASE_URL", "")
        self.anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
        self.service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
