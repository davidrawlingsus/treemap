# Environment Variables Documentation

Complete guide to configuring Vizualizd using environment variables.

---

## Quick Start

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Edit `.env.local` with your actual values

3. Required variables for local development:
   - `DATABASE_URL` (auto-configured for SQLite)
   - `JWT_SECRET_KEY` (change from default)
   - `FRONTEND_BASE_URL` (auto-configured for localhost)

---

## Configuration Loading Priority

Variables are loaded in this order (highest to lowest priority):

1. **System environment variables** (highest priority)
2. **`.env.local`** (git-ignored, for local development)
3. **`.env`** (if present, for defaults)
4. **Pydantic defaults** (lowest priority)

---

## Database Configuration

### `DATABASE_URL` (Required)

The primary database connection URL.

**Format**: `<dialect>://<user>:<password>@<host>:<port>/<database>`

**Examples**:
```bash
# Local SQLite (development)
DATABASE_URL=sqlite:///./treemap.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/vizualizd

# Railway PostgreSQL (auto-provided)
DATABASE_URL=postgresql://postgres:password@containers-us-west-123.railway.app:6789/railway
```

**Notes**:
- Railway automatically provides this variable
- SQLite is used by default for local development
- PostgreSQL URLs are automatically normalized to use `psycopg` driver

---

### `DATABASE_PUBLIC_URL` (Optional)

Alternative database URL for external access.

**Use Case**: Local development connecting to Railway database

**Example**:
```bash
DATABASE_PUBLIC_URL=postgresql://postgres:password@containers-us-west-123.railway.app:6789/railway
```

**Priority**: If set, this takes precedence over `DATABASE_URL`

---

## Application Configuration

### `ENVIRONMENT` (Optional)

Application environment mode.

**Valid Values**: `development`, `production`, `test`  
**Default**: `development`

**Example**:
```bash
ENVIRONMENT=production
```

**Effects**:
- Determines logging verbosity
- Affects error message detail
- Used for conditional feature flags

---

### `JWT_SECRET_KEY` (Required)

Secret key for JWT token signing and verification.

**Default**: `change-me` (⚠️ **MUST CHANGE IN PRODUCTION**)

**Generate Secure Key**:
```bash
openssl rand -hex 32
```

**Example**:
```bash
JWT_SECRET_KEY=8f7d3c2b1a9e4d6f5c8a7b3e2d1f9c8b7a6e5d4c3b2a1f8e7d6c5b4a3e2d1c0b
```

**Security**:
- Use different keys for dev/staging/prod
- Never commit to version control
- Rotate periodically
- Minimum 32 bytes recommended

---

### `JWT_ALGORITHM` (Optional)

Algorithm used for JWT encoding.

**Default**: `HS256`  
**Valid Values**: `HS256`, `HS384`, `HS512`

**Example**:
```bash
JWT_ALGORITHM=HS256
```

---

### `ACCESS_TOKEN_EXPIRE_MINUTES` (Optional)

JWT access token lifetime in minutes.

**Default**: `10080` (7 days)

**Examples**:
```bash
ACCESS_TOKEN_EXPIRE_MINUTES=60      # 1 hour
ACCESS_TOKEN_EXPIRE_MINUTES=1440    # 1 day
ACCESS_TOKEN_EXPIRE_MINUTES=10080   # 7 days (default)
```

---

## Magic Link Authentication

### `MAGIC_LINK_TOKEN_EXPIRE_MINUTES` (Optional)

Magic link validity period in minutes.

**Default**: `60` (1 hour)

**Example**:
```bash
MAGIC_LINK_TOKEN_EXPIRE_MINUTES=60
```

**Recommendation**: Keep short (15-60 minutes) for security

---

### `MAGIC_LINK_RATE_LIMIT_SECONDS` (Optional)

Minimum time between magic link requests from same email.

**Default**: `120` (2 minutes)

**Example**:
```bash
MAGIC_LINK_RATE_LIMIT_SECONDS=120
```

**Purpose**: Prevent spam and abuse

---

### `FRONTEND_BASE_URL` (Required)

Base URL where users access the frontend application.

**Default**: `http://localhost:3000`

**Examples**:
```bash
# Local development
FRONTEND_BASE_URL=http://localhost:8000

# Railway production
FRONTEND_BASE_URL=https://vizualizd-production.up.railway.app

# Custom domain
FRONTEND_BASE_URL=https://app.yourdomain.com
```

**Used For**:
- Generating magic link URLs
- CORS configuration
- Email templates

---

### `MAGIC_LINK_REDIRECT_PATH` (Optional)

Path to redirect users after clicking magic link.

**Default**: `/magic-login`

**Example**:
```bash
MAGIC_LINK_REDIRECT_PATH=/magic-login
```

**Full URL**: Constructed as `{FRONTEND_BASE_URL}{MAGIC_LINK_REDIRECT_PATH}?token=...&email=...`

---

## Email Service (Resend)

### `RESEND_API_KEY` (Optional, Required for Magic Links)

API key from Resend email service.

**Get Key**: https://resend.com/api-keys

**Example**:
```bash
RESEND_API_KEY=re_123abc456def789ghi012jkl345mno
```

**Required For**:
- Sending magic link emails
- Password reset emails
- User notifications

---

### `RESEND_FROM_EMAIL` (Optional, Required for Magic Links)

Email address to send from (must be verified domain).

**Example**:
```bash
RESEND_FROM_EMAIL=noreply@yourdomain.com
```

**Requirements**:
- Domain must be verified in Resend
- Must match Resend account configuration

---

### `RESEND_REPLY_TO_EMAIL` (Optional)

Email address for user replies.

**Example**:
```bash
RESEND_REPLY_TO_EMAIL=support@yourdomain.com
```

---

## OpenAI Integration

### `OPENAI_API_KEY` (Optional, Required for AI Summaries)

OpenAI API key for generating dimension summaries.

**Get Key**: https://platform.openai.com/api-keys

**Example**:
```bash
OPENAI_API_KEY=sk-proj-abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yz
```

**Used For**:
- Generating dimension summaries
- AI-powered insights
- Topic analysis

**Billing**: Usage is billed to your OpenAI account

---

## OAuth Providers (Optional)

### `GOOGLE_OAUTH_CLIENT_ID` (Optional)

Google OAuth 2.0 client ID.

**Get From**: https://console.cloud.google.com/apis/credentials

**Example**:
```bash
GOOGLE_OAUTH_CLIENT_ID=123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
```

**Note**: OAuth implementation is currently a stub

---

### `GOOGLE_OAUTH_CLIENT_SECRET` (Optional)

Google OAuth 2.0 client secret.

**Example**:
```bash
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-abcd1234efgh5678ijkl
```

---

## CORS Configuration

### `ADDITIONAL_CORS_ORIGINS` (Optional)

Additional allowed origins for CORS requests.

**Formats**:
```bash
# Comma-separated
ADDITIONAL_CORS_ORIGINS=http://localhost:3000,https://app.example.com

# JSON array
ADDITIONAL_CORS_ORIGINS=["http://localhost:3000","https://app.example.com"]
```

**Default Allowed**:
- Origin from `FRONTEND_BASE_URL`
- All `*.up.railway.app` domains (Railway deployments)
- `localhost` with any port

**Use Case**: Allow requests from additional domains or ports

---

## Environment-Specific Examples

### Local Development

```bash
DATABASE_URL=sqlite:///./treemap.db
ENVIRONMENT=development
JWT_SECRET_KEY=dev-secret-change-me
FRONTEND_BASE_URL=http://localhost:8000

# Optional: Connect to Railway database
# DATABASE_PUBLIC_URL=postgresql://postgres:pass@railway.host:6789/railway

# Optional: Enable features
OPENAI_API_KEY=sk-...
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=dev@yourdomain.com
```

---

### Railway Production

```bash
# Database (auto-provided by Railway)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Application
ENVIRONMENT=production
JWT_SECRET_KEY=${{JWT_SECRET}}  # Set in Railway dashboard
FRONTEND_BASE_URL=https://vizualizd-production.up.railway.app

# Magic Link
MAGIC_LINK_TOKEN_EXPIRE_MINUTES=60
MAGIC_LINK_RATE_LIMIT_SECONDS=120
MAGIC_LINK_REDIRECT_PATH=/magic-login

# Email (Required)
RESEND_API_KEY=${{RESEND_API_KEY}}
RESEND_FROM_EMAIL=noreply@yourdomain.com
RESEND_REPLY_TO_EMAIL=support@yourdomain.com

# OpenAI (Required)
OPENAI_API_KEY=${{OPENAI_API_KEY}}

# CORS (if needed)
ADDITIONAL_CORS_ORIGINS=https://yourdomain.com
```

---

### Test Environment

```bash
DATABASE_URL=sqlite:///:memory:
ENVIRONMENT=test
JWT_SECRET_KEY=test-secret
FRONTEND_BASE_URL=http://localhost:8000

# Disable external services in tests
RESEND_API_KEY=
OPENAI_API_KEY=
```

---

## Validation & Troubleshooting

### Check Configuration

```bash
# Verify env variables are loaded
cd backend
source venv/bin/activate
python -c "from app.config import get_settings; s = get_settings(); print(f'Environment: {s.environment}'); print(f'Frontend URL: {s.frontend_base_url}')"
```

### Common Issues

**Issue**: "Database connection failed"
- **Solution**: Check `DATABASE_URL` format and credentials
- **Verify**: `psql $DATABASE_URL` (for PostgreSQL)

**Issue**: "Email service not configured"
- **Solution**: Set all 3 Resend variables:
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
  - `RESEND_REPLY_TO_EMAIL`
- **Verify**: Domain is verified in Resend dashboard

**Issue**: "OpenAI API calls failing"
- **Solution**: Check `OPENAI_API_KEY` is valid
- **Verify**: Test key at https://platform.openai.com/api-keys
- **Check**: Account has credits available

**Issue**: "CORS errors in browser"
- **Solution**: Add origin to `ADDITIONAL_CORS_ORIGINS`
- **Format**: Must include protocol and port
- **Example**: `http://localhost:3000` not `localhost:3000`

---

## Security Best Practices

1. **JWT Secret Key**:
   - Generate with `openssl rand -hex 32`
   - Use different keys per environment
   - Never share or commit to git
   - Rotate every 90 days

2. **API Keys**:
   - Store in Railway dashboard (production)
   - Use `.env.local` (development, git-ignored)
   - Never commit to `.env` file
   - Rotate if compromised

3. **Database Credentials**:
   - Use Railway managed database (auto-rotated)
   - Don't share connection strings
   - Use `DATABASE_PUBLIC_URL` for temporary local access

4. **Email Configuration**:
   - Verify sender domain in Resend
   - Use different sender addresses per environment
   - Monitor email sending quotas

---

## Railway-Specific Configuration

### Setting Variables in Railway

1. Navigate to your Railway project
2. Click on your service
3. Go to "Variables" tab
4. Add/edit variables
5. Redeploy if needed

### Railway Auto-Provided Variables

These are automatically set by Railway:

- `DATABASE_URL` - PostgreSQL connection string
- `PORT` - Port to run the service on
- `RAILWAY_ENVIRONMENT` - Railway environment name

### Railway Variable References

Reference other Railway services:

```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
OPENAI_API_KEY=${{OPENAI_API_KEY}}  # Shared variable
```

---

## Development Workflow

### First-Time Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd vizualizd

# 2. Create local environment file
cp .env.example .env.local

# 3. Edit with your values
nano .env.local  # or use your editor

# 4. Set minimum required values:
#    - DATABASE_URL (default SQLite is fine)
#    - JWT_SECRET_KEY (change from default)
#    - FRONTEND_BASE_URL (default localhost:8000 is fine)

# 5. Optional: Add API keys for full functionality
#    - OPENAI_API_KEY (for AI summaries)
#    - RESEND_API_KEY (for magic link emails)
```

### Connecting to Railway Database Locally

```bash
# 1. Get connection string from Railway dashboard
#    (Variables tab → DATABASE_URL)

# 2. Set in .env.local
DATABASE_PUBLIC_URL=postgresql://postgres:pass@railway-host:port/railway

# 3. Restart backend server
```

---

## Reference

For more information:
- **Resend Documentation**: https://resend.com/docs
- **OpenAI API**: https://platform.openai.com/docs/api-reference
- **Railway Variables**: https://docs.railway.app/guides/variables
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

---

## Support

If you encounter configuration issues:
1. Check this documentation
2. Verify variable format matches examples
3. Check application logs for specific errors
4. Ensure all required dependencies are installed

---

**Last Updated**: December 29, 2025  
**Version**: 1.0

