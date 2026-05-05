# Supabase bootstrap

Use this with the existing migration and seed pipeline:

1. Create a hosted Supabase project.
2. In Authentication:
   - keep email/password enabled
   - disable public signups
   - set Site URL to `https://bearhaoyuli.github.io/private-stock-signal-dashboard/`
   - add the same URL to Redirect URLs
3. In SQL editor, run:
   - `supabase/migrations/0001_init.sql`
4. Create your single login user in Auth > Users.
5. Put project values into `.env`.
6. Run:

```bash
PYTHONPATH=backend python backend/scripts/seed_mock_data.py
```

That script will persist to Supabase automatically when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.
