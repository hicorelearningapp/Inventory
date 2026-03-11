from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)
