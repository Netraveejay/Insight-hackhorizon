"""Load seed data and run the pipeline."""

from app.db import SessionLocal, init_db
from app.orchestrator import Orchestrator
from app.seed.generate import LATEST_WEEK


def main():
    init_db()
    db = SessionLocal()
    try:
        orch = Orchestrator(db)
        result = orch.run_pipeline(week=LATEST_WEEK, cadence="seed")
        print(f"Pipeline complete: {result.model_dump()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
