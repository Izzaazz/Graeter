import os
from alembic import context
from sqlalchemy import create_engine
from app.db import Base
config=context.config
def run():
    engine=create_engine(os.getenv('DATABASE_URL','sqlite:///./dispatch.db'))
    with engine.connect() as conn:
        context.configure(connection=conn,target_metadata=Base.metadata)
        with context.begin_transaction():context.run_migrations()
run()
