"""Create the harness persistence schema."""

from alembic import op

from app.harness.db_models import HARNESS_SCHEMA, HarnessBase

revision = "0001_harness"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(f'create schema if not exists "{HARNESS_SCHEMA}"')
    HarnessBase.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    HarnessBase.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
