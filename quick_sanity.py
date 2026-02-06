# quick_sanity.py
import numpy as np, pandas as pd
from datetime import datetime, timedelta
from daily_report import serialize_datetime

payload = {
    "a": np.array([1, 2, np.nan]),
    "b": pd.Series([1.0, np.nan, 3.5]),
    "c": pd.DataFrame({"x":[1,2], "y":[pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]}),
    "d": [datetime.utcnow(), timedelta(hours=3)],
    "e": {"nested": [np.float64("nan"), np.float64("inf"), 5.0]}
}
import json
print(json.dumps(serialize_datetime(payload)))
