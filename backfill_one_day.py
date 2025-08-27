# backfill_one_day.py
from datetime import date, timedelta
from app import create_app
from app.models import db, User
from tasks.data_ingestion import backfill_user_data

app = create_app()
with app.app_context():
    user_id = "sample_user"              # change if needed
    day = date(2025, 8, 14)              # pick a day you expect to have data
    res = backfill_user_data(
        user_id,
        day.isoformat(),                 # start_date (YYYY-MM-DD)
        (day + timedelta(days=1)).isoformat()  # end_date (exclusive)
    )
    print(res)
