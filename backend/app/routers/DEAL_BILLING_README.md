# Custom Deal Billing

Founder-controlled bespoke deal billing with phased payment schedules.

**This is NOT the SaaS subscription system.** It is a completely separate flow for manually negotiated commercial agreements.

## How It Differs From SaaS Billing

| Aspect | SaaS Billing | Custom Deal Billing |
|--------|-------------|-------------------|
| Who creates | Self-serve customer | Founder only |
| Pricing | Fixed plans (basic/pro) | Bespoke per deal |
| Checkout mode | `subscription` | `setup` (card save only) |
| Billing structure | Simple recurring | Phased schedule (varied amounts) |
| DB tables | `plans`, `subscriptions` | `custom_deals`, `custom_deal_phases`, `custom_deal_stripe_state` |
| Router | `/api/billing/*` | `/api/deal-billing/*` (public) + `/api/founder/custom-deals` (admin) |
| Service | `stripe_service.py` | `custom_deal_service.py` |
| Webhook endpoint | `/api/billing/webhook` | `/api/deal-billing/webhook` |

## Admin Workflow

1. Go to **Founder Admin > Custom Deal Billing**
2. Click **+ New Deal**
3. Fill in client details, deal title, currency
4. Define billing phases (e.g. month 1: 8000, month 2: 6000, month 3+: 5000/mo)
5. Save the deal
6. Copy the unique deal page link
7. Send the link to the client

## Client Workflow

1. Client opens the deal page link
2. Sees the payment schedule and terms (no charge today)
3. Enters card details via embedded Stripe Checkout (setup mode)
4. Card is saved, no payment taken
5. Stripe webhook fires, backend creates the subscription schedule
6. Charges happen automatically on the defined dates

## Stripe Objects Involved

- **Customer**: Created per deal, tagged with `source: custom_deal_billing`
- **Checkout Session**: `mode: setup`, `ui_mode: embedded` — saves card without charging
- **SetupIntent**: Created automatically by Checkout Session
- **Payment Method**: Attached to customer, set as default for invoicing
- **Product + Price**: Created dynamically per phase (each phase has a unique amount)
- **Subscription Schedule**: Phases map to schedule phases with `iterations` for fixed or open-ended for recurring

### Why Dynamic Products/Prices?

Each deal has bespoke amounts (e.g. 8000, 6000, 5000). Reusable price templates don't work because amounts vary per deal. Products are named descriptively (`Custom Deal: Acme Corp - Phase 1`) for easy identification in the Stripe dashboard.

## Webhook Flow

```
Stripe fires: checkout.session.completed (mode=setup)
    |
    v
Webhook endpoint: /api/deal-billing/webhook
    |
    v
Check metadata.source == "custom_deal_billing"  (ignore SaaS sessions)
    |
    v
Idempotency check: if schedule already exists, skip
    |
    v
Retrieve SetupIntent -> get payment_method
    |
    v
Set payment method as customer default for invoicing
    |
    v
Update deal status: card_captured
    |
    v
Create Subscription Schedule with phased billing
    |
    v
Update deal status: billing_schedule_active
```

## Environment Variables

Add these to your `.env`:

```
# Already set for SaaS billing:
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional: separate webhook secret for deal billing
# Falls back to STRIPE_WEBHOOK_SECRET if not set
STRIPE_DEAL_WEBHOOK_SECRET=whsec_...

# Optional: base URL for deal page links
# Falls back to FRONTEND_BASE_URL
DEAL_PAGE_BASE_URL=https://mapthegap.ai
```

## Local Testing with Stripe Test Mode

### 1. Set up Stripe CLI for webhooks

```bash
stripe listen --forward-to localhost:8000/api/deal-billing/webhook
```

Copy the webhook signing secret it gives you into `STRIPE_DEAL_WEBHOOK_SECRET`.

### 2. Create a deal

Use the admin page at `/founder_custom_deals.html` or via API:

```bash
curl -X POST http://localhost:8000/api/founder/custom-deals \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "client_email": "test@example.com",
    "deal_title": "Test Deal",
    "currency": "gbp",
    "phases": [
      {"phase_order": 0, "label": "Project begins", "amount_cents": 800000, "duration_months": 1},
      {"phase_order": 1, "label": "Month 2", "amount_cents": 600000, "duration_months": 1},
      {"phase_order": 2, "label": "Month 3 onward", "amount_cents": 500000, "is_recurring_indefinitely": true}
    ]
  }'
```

### 3. Open the deal page

Copy the public URL from the admin panel and open it in your browser.

### 4. Use Stripe test card

Enter `4242 4242 4242 4242` with any future expiry and CVC.

### 5. Verify in Stripe Dashboard

Check:
- Customer created with `source: custom_deal_billing` metadata
- Subscription Schedule created with 3 phases
- Phase 1: 1 iteration at 8000
- Phase 2: 1 iteration at 6000
- Phase 3: open-ended at 5000/month

### Testing phased schedules safely

In test mode, Stripe won't actually charge. You can use the Stripe Dashboard or CLI to:
- View the subscription schedule: `stripe subscription_schedules list`
- Advance the test clock (if using Stripe test clocks) to trigger phases
- Cancel a schedule: `stripe subscription_schedules cancel sub_sched_xxx`

## Database Tables

- `custom_deals` — deal records with client info, status, public token, page copy
- `custom_deal_phases` — billing phases (amount, duration, recurring flag)
- `custom_deal_stripe_state` — all Stripe IDs and webhook state (1:1 with deal)

Run the migration: `alembic upgrade head`

## API Endpoints

### Founder Admin (JWT required, founder role)
- `GET /api/founder/custom-deals` — list deals (optional `?status=` filter)
- `GET /api/founder/custom-deals/{id}` — get deal with phases + Stripe state
- `POST /api/founder/custom-deals` — create deal
- `PUT /api/founder/custom-deals/{id}` — update deal
- `DELETE /api/founder/custom-deals/{id}` — delete (draft/page_generated only)
- `POST /api/founder/custom-deals/{id}/regenerate-token` — new public URL
- `GET /api/founder/custom-deals/{id}/public-url` — get the deal page URL
- `GET /api/founder/custom-deals/statuses/list` — list all status values

### Public (no auth, secured by unguessable token)
- `GET /api/deal-billing/page/{token}` — deal page data
- `POST /api/deal-billing/checkout/{token}` — create Stripe Checkout session
- `GET /api/deal-billing/status/{token}` — check setup status
- `GET /api/deal-billing/publishable-key` — Stripe publishable key
- `POST /api/deal-billing/webhook` — Stripe webhook endpoint

## Tests

```bash
cd backend
python -m pytest tests/test_custom_deal.py -v
```

Covers: phase validation, deal creation schemas, public token generation, webhook idempotency, status transitions.

## Caveats / Future Improvements

- **No email sending**: The admin copies and sends the deal link manually. Could add Resend integration later.
- **No cancellation automation**: Cancellation URL is informational. Could add a cancel endpoint that releases the Stripe schedule.
- **No payment method update flow**: If a card expires, would need a new setup session. Could add a "update payment method" flow.
- **No deal templates**: Each deal is created from scratch. Could add preset templates for common deal shapes.
- **Schedule modifications**: Once a schedule is created, changing phases requires Stripe schedule amendment (not yet implemented).
