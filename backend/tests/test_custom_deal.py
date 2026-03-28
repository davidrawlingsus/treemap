"""
Tests for the custom deal billing flow.
Covers: schema validation, service logic, webhook idempotency, status transitions.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.schemas.custom_deal import (
    CustomDealCreate,
    DealPhaseCreate,
    CustomDealUpdate,
)
from app.models.custom_deal import DealStatus
from app.services.custom_deal_service import generate_public_token


# ─── Schema validation ─────────────────────────────────────────────

class TestDealPhaseValidation:
    """Test Pydantic validation on billing phases."""

    def test_valid_fixed_phase(self):
        phase = DealPhaseCreate(
            phase_order=0, amount_cents=800000, duration_months=1, is_recurring_indefinitely=False
        )
        assert phase.amount_cents == 800000
        assert phase.duration_months == 1

    def test_valid_recurring_phase(self):
        phase = DealPhaseCreate(
            phase_order=2, amount_cents=500000, is_recurring_indefinitely=True
        )
        assert phase.is_recurring_indefinitely is True
        assert phase.duration_months is None

    def test_recurring_phase_with_duration_fails(self):
        with pytest.raises(Exception):
            DealPhaseCreate(
                phase_order=2, amount_cents=500000, duration_months=3, is_recurring_indefinitely=True
            )

    def test_fixed_phase_without_duration_fails(self):
        with pytest.raises(Exception):
            DealPhaseCreate(
                phase_order=0, amount_cents=800000, is_recurring_indefinitely=False
            )

    def test_zero_amount_fails(self):
        with pytest.raises(Exception):
            DealPhaseCreate(
                phase_order=0, amount_cents=0, duration_months=1, is_recurring_indefinitely=False
            )

    def test_negative_amount_fails(self):
        with pytest.raises(Exception):
            DealPhaseCreate(
                phase_order=0, amount_cents=-100, duration_months=1, is_recurring_indefinitely=False
            )


class TestDealCreateValidation:
    """Test full deal creation schema validation."""

    def _make_phases(self):
        return [
            DealPhaseCreate(phase_order=0, label="Phase 1", amount_cents=800000, duration_months=1),
            DealPhaseCreate(phase_order=1, label="Phase 2", amount_cents=600000, duration_months=1),
            DealPhaseCreate(phase_order=2, label="Ongoing", amount_cents=500000, is_recurring_indefinitely=True),
        ]

    def test_valid_deal(self):
        deal = CustomDealCreate(
            client_name="Acme Corp",
            client_email="ceo@acme.com",
            deal_title="Acme Website Redesign",
            currency="gbp",
            phases=self._make_phases(),
        )
        assert deal.client_name == "Acme Corp"
        assert len(deal.phases) == 3

    def test_empty_phases_fails(self):
        with pytest.raises(Exception):
            CustomDealCreate(
                client_name="Acme Corp",
                client_email="ceo@acme.com",
                deal_title="Acme Deal",
                phases=[],
            )

    def test_duplicate_phase_orders_fails(self):
        with pytest.raises(Exception):
            CustomDealCreate(
                client_name="Acme Corp",
                client_email="ceo@acme.com",
                deal_title="Acme Deal",
                phases=[
                    DealPhaseCreate(phase_order=0, amount_cents=800000, duration_months=1),
                    DealPhaseCreate(phase_order=0, amount_cents=600000, duration_months=1),
                ],
            )

    def test_multiple_recurring_phases_fails(self):
        with pytest.raises(Exception):
            CustomDealCreate(
                client_name="Acme Corp",
                client_email="ceo@acme.com",
                deal_title="Acme Deal",
                phases=[
                    DealPhaseCreate(phase_order=0, amount_cents=800000, is_recurring_indefinitely=True),
                    DealPhaseCreate(phase_order=1, amount_cents=600000, is_recurring_indefinitely=True),
                ],
            )

    def test_recurring_not_last_fails(self):
        with pytest.raises(Exception):
            CustomDealCreate(
                client_name="Acme Corp",
                client_email="ceo@acme.com",
                deal_title="Acme Deal",
                phases=[
                    DealPhaseCreate(phase_order=0, amount_cents=800000, is_recurring_indefinitely=True),
                    DealPhaseCreate(phase_order=1, amount_cents=600000, duration_months=1),
                ],
            )

    def test_missing_required_fields_fails(self):
        with pytest.raises(Exception):
            CustomDealCreate(
                client_name="",
                client_email="ceo@acme.com",
                deal_title="Deal",
                phases=[DealPhaseCreate(phase_order=0, amount_cents=100, duration_months=1)],
            )

    def test_all_fixed_phases_valid(self):
        """A deal with no recurring phase is valid (e.g. a fixed project)."""
        deal = CustomDealCreate(
            client_name="Test",
            client_email="t@t.com",
            deal_title="Fixed Deal",
            phases=[
                DealPhaseCreate(phase_order=0, amount_cents=500000, duration_months=1),
                DealPhaseCreate(phase_order=1, amount_cents=300000, duration_months=2),
            ],
        )
        assert len(deal.phases) == 2


class TestDealUpdateValidation:
    """Test update schema validation."""

    def test_partial_update(self):
        update = CustomDealUpdate(client_name="New Name")
        assert update.client_name == "New Name"
        assert update.phases is None

    def test_update_with_empty_phases_fails(self):
        with pytest.raises(Exception):
            CustomDealUpdate(phases=[])


# ─── Public token generation ──────────────────────────────────────

class TestPublicToken:
    def test_token_length(self):
        token = generate_public_token()
        assert len(token) >= 32

    def test_tokens_unique(self):
        tokens = {generate_public_token() for _ in range(100)}
        assert len(tokens) == 100


# ─── Webhook idempotency ─────────────────────────────────────────

class TestWebhookIdempotency:
    """Test that webhook processing is idempotent."""

    @patch("app.services.custom_deal_service._configure_stripe")
    @patch("app.services.custom_deal_service.stripe")
    def test_duplicate_webhook_skipped(self, mock_stripe, mock_configure):
        """If schedule already exists, webhook should skip processing."""
        from app.services.custom_deal_service import handle_checkout_session_completed

        # Create mock deal with existing schedule
        mock_stripe_state = MagicMock()
        mock_stripe_state.stripe_subscription_schedule_id = "sub_sched_existing"
        mock_stripe_state.stripe_customer_id = "cus_123"

        mock_deal = MagicMock()
        mock_deal.id = uuid4()
        mock_deal.stripe_state = mock_stripe_state

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_deal

        session_data = {
            "id": "cs_test_123",
            "metadata": {"custom_deal_id": str(mock_deal.id), "source": "custom_deal_billing"},
            "setup_intent": "seti_123",
            "customer": "cus_123",
        }

        # Should not raise, should not create new schedule
        handle_checkout_session_completed(session_data, mock_db)

        # Stripe SetupIntent should NOT be retrieved (we short-circuited)
        mock_stripe.SetupIntent.retrieve.assert_not_called()

    def test_non_deal_session_ignored(self):
        """Sessions without custom_deal_billing source should be ignored."""
        from app.services.custom_deal_service import handle_checkout_session_completed

        mock_db = MagicMock()
        session_data = {
            "id": "cs_test_saas",
            "metadata": {"source": "saas_billing"},
        }

        handle_checkout_session_completed(session_data, mock_db)
        # Should not query the database
        mock_db.query.assert_not_called()


# ─── Status transitions ──────────────────────────────────────────

class TestStatusTransitions:
    def test_all_statuses_defined(self):
        expected = {
            "draft", "page_generated", "awaiting_card_setup", "card_captured",
            "billing_schedule_active", "cancelled", "payment_failed", "completed",
        }
        actual = {s.value for s in DealStatus}
        assert actual == expected

    def test_status_string_representation(self):
        assert DealStatus.draft.value == "draft"
        assert DealStatus.billing_schedule_active.value == "billing_schedule_active"
