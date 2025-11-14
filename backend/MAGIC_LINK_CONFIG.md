# Magic Link Authentication Configuration

## Required Environment Variables

For magic link authentication to work correctly, you need to set these environment variables:

### Production (Railway)

Set these in Railway's environment variables:

```
FRONTEND_BASE_URL=https://vizualizd.marketably.ai
MAGIC_LINK_REDIRECT_PATH=/
MAGIC_LINK_TOKEN_EXPIRE_MINUTES=60
MAGIC_LINK_RATE_LIMIT_SECONDS=120
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=noreply@marketably.ai
RESEND_REPLY_TO_EMAIL=support@marketably.ai
```

### Local Development

In `backend/.env.local`:

```
FRONTEND_BASE_URL=http://localhost:3000
MAGIC_LINK_REDIRECT_PATH=/
MAGIC_LINK_TOKEN_EXPIRE_MINUTES=60
MAGIC_LINK_RATE_LIMIT_SECONDS=120
```

## Important Notes

1. **FRONTEND_BASE_URL** must match the actual URL where your frontend is hosted
   - Production: `https://vizualizd.marketably.ai`
   - Local: `http://localhost:3000` or `http://localhost:8000` depending on your setup

2. **MAGIC_LINK_REDIRECT_PATH** should be `/` or empty (will redirect to root)

3. **Token Expiration**: Default is 60 minutes. Tokens expire after this time.

4. **Rate Limiting**: Default is 120 seconds (2 minutes) between magic link requests

## Troubleshooting

If magic link verification fails:

1. Check server logs for detailed error messages (now includes logging)
2. Verify FRONTEND_BASE_URL matches the actual frontend URL
3. Ensure the user's email domain is in the `authorized_domains` table
4. Verify the authorized domain is linked to at least one active client
5. Check that the token hasn't expired (default: 60 minutes)

## Database Requirements

The user must have:
- An entry in the `authorized_domains` table matching their email domain
- The authorized domain must be linked to at least one active client via `authorized_domain_clients` table
- Active memberships will be auto-created when they request a magic link

## Logging

Enhanced logging has been added to help diagnose issues:
- Token generation and storage
- Token verification and validation
- Hash comparison details
- Expiration checks

Check your application logs for detailed information about failed verification attempts.

