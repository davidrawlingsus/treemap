# Production Database Deployment Guide

This guide ensures the production database has the same tables and data structure as the feature branch.

## Prerequisites

- Railway CLI installed and authenticated
- Access to production database
- All code changes merged to master branch

## Deployment Steps

### Step 1: Run Database Migration Script

Run the deployment script on production to:
- Check database connection
- Verify all required tables exist
- Run pending Alembic migrations
- Verify process_voc table structure
- Map client_uuid in process_voc rows to clients table

```bash
# From Railway dashboard or CLI
railway run python deploy_to_production.py
```

Or via Railway CLI:
```bash
cd backend
railway run python deploy_to_production.py
```

### Step 2: Verify Migration Status

Check if all migrations are applied:

```bash
railway run alembic current
```

You should see migration `003` (add users and memberships).

### Step 3: Run Migrations Manually (if needed)

If the script doesn't run migrations automatically:

```bash
railway run alembic upgrade head
```

### Step 4: Verify Database State

Check that all tables exist:

```bash
railway run python -c "from app.database import engine; from sqlalchemy import inspect; print([t for t in inspect(engine).get_table_names()])"
```

Required tables:
- `clients`
- `users`
- `memberships`
- `process_voc`
- `data_sources` (may still exist for backward compatibility)
- `dimension_names` (may still exist for backward compatibility)

### Step 5: Verify process_voc Data

Check that process_voc has data and client_uuid mappings:

```bash
railway run python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM process_voc'))
    print(f'Total rows: {result.scalar()}')
    result = conn.execute(text('SELECT COUNT(*) FROM process_voc WHERE client_uuid IS NOT NULL'))
    print(f'Rows with client_uuid: {result.scalar()}')
"
```

### Step 6: Map client_uuid if Needed

If process_voc rows have NULL client_uuid but have client_name, the deployment script will automatically map them. If not, you can manually run:

```bash
railway run python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('''
        UPDATE process_voc pv
        SET client_uuid = c.id
        FROM clients c
        WHERE pv.client_name = c.name
        AND pv.client_uuid IS NULL
    '''))
    conn.commit()
    print('Updated client_uuid mappings')
"
```

## What the Deployment Script Does

1. **Database Connection Check** - Verifies connection works
2. **Table Verification** - Checks all required tables exist
3. **Migration Execution** - Runs Alembic migrations up to head
4. **process_voc Structure Check** - Verifies table has correct columns
5. **Client UUID Mapping** - Maps client_name to client_uuid in process_voc

## Troubleshooting

### Migration Fails

If migrations fail, check:
- Database connection string is correct
- All required dependencies are installed
- Previous migrations were applied successfully

### process_voc Table Missing

If process_voc doesn't exist, it means it wasn't created in production. You may need to:
1. Check if it exists in production schema
2. Create it manually if needed
3. Migrate data from data_sources if applicable

### client_uuid is NULL

The deployment script will automatically map client_name to client_uuid. If it doesn't work:
- Verify clients exist in the clients table
- Check that client names match exactly (case-sensitive)
- Manually update rows if needed

## Verification Checklist

After deployment, verify:

- [ ] All migrations applied (`alembic current` shows `003`)
- [ ] All required tables exist
- [ ] process_voc table has correct structure
- [ ] process_voc has data (row count > 0)
- [ ] client_uuid is mapped for process_voc rows
- [ ] API endpoints work (`/api/voc/clients`, `/api/voc/data`, etc.)
- [ ] Frontend can load clients and data

## Rollback Plan

If something goes wrong:

1. **Revert code**: `git revert <merge-commit>`
2. **Revert migrations**: `alembic downgrade -1` (if needed)
3. **Restore from backup**: If you have a database backup

## Notes

- The `process_voc` table already exists in production (from Railway database)
- The main work is ensuring migrations are applied and client_uuid is mapped
- The old `data_sources` table can remain for backward compatibility but is no longer used

