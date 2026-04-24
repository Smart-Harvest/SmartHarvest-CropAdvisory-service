"""create advisory_history table

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "advisory_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("soil_type", sa.String(100), nullable=False),
        sa.Column("weather_data", JSON, nullable=True),
        sa.Column("recommended_crops", JSON, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_advisory_history_user_id", "advisory_history", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_advisory_history_user_id")
    op.drop_table("advisory_history")
