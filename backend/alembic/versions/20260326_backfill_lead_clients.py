"""backfill_existing_leadgen_runs_as_lead_clients

Creates Client records for existing LeadgenVocRuns that don't yet have
a converted_client_uuid, copies their rows to process_voc, and sets up
authorized_domain links.

Revision ID: 2007d0bd6fd5
Revises: 16a026205ee8
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = "2007d0bd6fd5"
down_revision = "16a026205ee8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Get the first active founder to assign as owner
    founder_row = conn.execute(
        text("SELECT id FROM users WHERE is_founder = true AND is_active = true LIMIT 1")
    ).first()
    if not founder_row:
        # No founder — skip backfill (will be handled on next run)
        return
    founder_id = founder_row[0]

    # Temporarily disable the process_voc insert permission trigger for backfill
    conn.execute(text("""
        ALTER TABLE process_voc DISABLE TRIGGER ALL
    """))

    # Mark existing converted clients as is_lead
    conn.execute(
        text("""
            UPDATE clients SET is_lead = true
            WHERE id IN (
                SELECT converted_client_uuid FROM leadgen_voc_runs
                WHERE converted_client_uuid IS NOT NULL
            )
        """)
    )

    # Find runs that have no converted_client_uuid yet
    unconverted = conn.execute(
        text("""
            SELECT run_id, company_name, company_domain, company_url
            FROM leadgen_voc_runs
            WHERE converted_client_uuid IS NULL
            ORDER BY created_at ASC
        """)
    ).fetchall()

    for run_id, company_name, company_domain, company_url in unconverted:
        # Generate a safe slug
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", company_domain.lower()).strip("-") or "lead"

        # Ensure name uniqueness
        name = company_name
        suffix = 2
        while conn.execute(text("SELECT 1 FROM clients WHERE name = :n"), {"n": name}).first():
            name = f"{company_name} ({suffix})"
            suffix += 1

        # Ensure slug uniqueness
        base_slug = slug
        suffix = 2
        while conn.execute(text("SELECT 1 FROM clients WHERE slug = :s"), {"s": slug}).first():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        # Create the client
        conn.execute(
            text("""
                INSERT INTO clients (id, name, slug, is_active, is_lead, founder_user_id,
                                     client_url, leadgen_run_id, created_at)
                VALUES (gen_random_uuid(), :name, :slug, true, true, :founder_id,
                        :client_url, :run_id, now())
            """),
            {
                "name": name,
                "slug": slug,
                "founder_id": str(founder_id),
                "client_url": company_url,
                "run_id": run_id,
            },
        )

        # Get the new client id
        client_row = conn.execute(
            text("SELECT id FROM clients WHERE leadgen_run_id = :rid"),
            {"rid": run_id},
        ).first()
        if not client_row:
            continue
        client_id = client_row[0]

        # Update the run
        conn.execute(
            text("""
                UPDATE leadgen_voc_runs
                SET converted_client_uuid = :cid, converted_at = now()
                WHERE run_id = :rid
            """),
            {"cid": str(client_id), "rid": run_id},
        )

        # Copy rows to process_voc
        conn.execute(
            text("""
                INSERT INTO process_voc (
                    respondent_id, created, last_modified, client_id, client_name,
                    project_id, project_name, total_rows, data_source,
                    dimension_ref, dimension_name, value, overall_sentiment,
                    topics, survey_metadata, question_text, question_type,
                    processed, client_uuid, created_at, updated_at
                )
                SELECT
                    respondent_id, created, last_modified, client_id, client_name,
                    project_id, project_name, total_rows, data_source,
                    dimension_ref, dimension_name, value, overall_sentiment,
                    topics, survey_metadata, question_text, question_type,
                    processed, :client_uuid, now(), now()
                FROM leadgen_voc_rows
                WHERE run_id = :rid
            """),
            {"client_uuid": str(client_id), "rid": run_id},
        )

        # Set up authorized domain
        normalized_domain = company_domain.lower().strip()
        if normalized_domain:
            domain_row = conn.execute(
                text("SELECT id FROM authorized_domains WHERE domain = :d"),
                {"d": normalized_domain},
            ).first()
            if not domain_row:
                conn.execute(
                    text("""
                        INSERT INTO authorized_domains (id, domain, created_at, updated_at)
                        VALUES (gen_random_uuid(), :d, now(), now())
                    """),
                    {"d": normalized_domain},
                )
                domain_row = conn.execute(
                    text("SELECT id FROM authorized_domains WHERE domain = :d"),
                    {"d": normalized_domain},
                ).first()

            if domain_row:
                domain_id = domain_row[0]
                existing_link = conn.execute(
                    text("""
                        SELECT 1 FROM authorized_domain_clients
                        WHERE domain_id = :did AND client_id = :cid
                    """),
                    {"did": str(domain_id), "cid": str(client_id)},
                ).first()
                if not existing_link:
                    conn.execute(
                        text("""
                            INSERT INTO authorized_domain_clients (domain_id, client_id, created_at, updated_at)
                            VALUES (:did, :cid, now(), now())
                        """),
                        {"did": str(domain_id), "cid": str(client_id)},
                    )

    # Re-enable triggers
    conn.execute(text("ALTER TABLE process_voc ENABLE TRIGGER ALL"))


def downgrade() -> None:
    conn = op.get_bind()
    # Remove process_voc rows for lead clients and delete lead clients
    conn.execute(
        text("""
            DELETE FROM process_voc
            WHERE client_uuid IN (SELECT id FROM clients WHERE is_lead = true)
        """)
    )
    # Note: we don't delete the clients themselves in downgrade
    # as that would cascade and could lose data. The is_lead column
    # removal is handled by the previous migration's downgrade.
