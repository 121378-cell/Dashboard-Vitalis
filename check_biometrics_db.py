import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.db.session import SessionLocal
from app.models.biometrics import Biometrics
import json

db = SessionLocal()
print("=== Recent biometrics in database ===\n")

recent = db.query(Biometrics).filter(
    Biometrics.user_id == "default_user"
).order_by(Biometrics.date.desc()).limit(10).all()

for b in recent:
    print(f"Date: {b.date}")
    print(f"  Source: {b.source}")
    try:
        data = json.loads(b.data)
        print(f"  Data: {json.dumps(data, indent=4)[:500]}")
    except:
        print(f"  Raw data: {b.data}")
    print()

db.close()