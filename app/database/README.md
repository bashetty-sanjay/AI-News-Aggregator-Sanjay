# Database Management

## Environment Configuration

The system supports two environments: **LOCAL** and **PRODUCTION**.

### Setting Environment

Set the `ENVIRONMENT` variable in your `.env` file:

```bash
# For local development
ENVIRONMENT=LOCAL

# For production (Render)
ENVIRONMENT=PRODUCTION
```

If not set, defaults to `LOCAL`.

### Database Connection

The system automatically detects the environment based on:
1. `ENVIRONMENT` variable
2. Database URL (if contains `render.com` or `amazonaws.com`, treated as PRODUCTION)

**Local Development:**
- Uses `POSTGRES_*` environment variables
- Defaults to `localhost:5432`

**Production (Render):**
- Uses `DATABASE_URL` (automatically provided by Render)
- No manual configuration needed

## Migration Scripts

### Check Database Connection

```bash
python app/database/check_connection.py
```

Shows:
- Current environment (LOCAL/PRODUCTION)
- Database connection status
- Table information
- Column existence

### Run Migration

```bash
# Local database
python app/database/migrate_add_sent_at.py

# Production database (requires confirmation)
ENVIRONMENT=PRODUCTION python app/database/migrate_add_sent_at.py
```

**Safety Features:**
- Shows environment and database info before running
- Requires explicit confirmation for PRODUCTION migrations
- Safe to run multiple times (uses `IF NOT EXISTS`)

## Switching Environments

### Local Development
```bash
# In .env file
ENVIRONMENT=LOCAL
DATABASE_URL=  # Leave empty or use local connection string
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_news_aggregator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### Production (Render)
```bash
# In Render dashboard, set:
ENVIRONMENT=PRODUCTION
# DATABASE_URL is automatically set by Render
```

### Manual Production Migration

To run migrations on production database locally:

1. Get production `DATABASE_URL` from Render dashboard
2. Set environment variables:
```bash
export ENVIRONMENT=PRODUCTION
export DATABASE_URL=postgresql://user:pass@host:port/dbname
```
3. Run migration:
```bash
python app/database/migrate_add_sent_at.py
```
4. Confirm when prompted (type 'yes')

## Best Practices

1. **Always check connection first** before running migrations
2. **Use LOCAL for development** - safer and faster
3. **Double-check environment** before production migrations
4. **Keep .env file local** - never commit production credentials
5. **Use Render environment variables** for production deployments

