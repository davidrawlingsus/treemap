"""seed product_context_extract prompt

Revision ID: 051
Revises: 050
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None

PROMPT_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

SYSTEM_MESSAGE = """\
You are an expert at extracting product information from e-commerce product detail pages (PDPs).

You will receive the raw text content of a PDP. Extract the following into a structured, readable format suitable for use when generating ads and marketing emails:

1. **Product name** – The main product title/name
2. **Pricing** – Price, any discounts, payment options, subscription pricing if applicable
3. **Unique features / differentiators** – Key benefits, specs, or selling points that distinguish this product
4. **Proof elements** – Reviews, ratings, certifications, awards, guarantees, testimonials
5. **Risk reversal** – Return policy, warranty, money-back guarantee, trial period

Output as clear, concise text that can be used as context for AI-generated ad copy and email content. Use headers (##) for sections if helpful. Be selective – include only the most relevant information for marketing purposes. Avoid redundant or overly promotional language from the page."""


def upgrade():
    prompts = sa.table(
        "prompts",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("version", sa.Integer),
        sa.column("prompt_type", sa.String),
        sa.column("system_message", sa.Text),
        sa.column("prompt_purpose", sa.String),
        sa.column("status", sa.String),
        sa.column("client_facing", sa.Boolean),
        sa.column("all_clients", sa.Boolean),
        sa.column("llm_model", sa.String),
    )
    op.bulk_insert(prompts, [
        {
            "id": PROMPT_ID,
            "name": "Product Context Extraction",
            "version": 1,
            "prompt_type": "system",
            "system_message": SYSTEM_MESSAGE,
            "prompt_purpose": "product_context_extract",
            "status": "live",
            "client_facing": False,
            "all_clients": True,
            "llm_model": "gpt-4o-mini",
        }
    ])


def downgrade():
    op.execute(
        sa.text("DELETE FROM prompts WHERE id = :id").bindparams(id=str(PROMPT_ID))
    )
