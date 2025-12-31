import json
from datetime import datetime

data = {
    "source": "idokep.hu",
    "generated_at": datetime.now().isoformat(),
    "current": {
        "temperature": None,
        "condition": None,
        "icon": None
    },
    "forecast_7d": []
}

with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("idokep.json létrehozva")
