import requests
import os
from datetime import datetime

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

# 🔧 Change les IDs selon tes ligues (tu peux en mettre plusieurs)
LEAGUES = {
    "Ligue 1": "4334",
    "Champions League": "4480",
}

today = datetime.utcnow().strftime("%Y-%m-%d")
lines = []

for league_name, league_id in LEAGUES.items():
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={today}&l={league_id}"
    data = requests.get(url).json()

    if not data.get("events"):
        continue

    lines.append(f"\n**⚽ {league_name}**")

    for m in data["events"]:
        home = m["strHomeTeam"]
        away = m["strAwayTeam"]
        hs = m["intHomeScore"] if m["intHomeScore"] is not None else "-"
        as_ = m["intAwayScore"] if m["intAwayScore"] is not None else "-"
        status = m.get("strStatus") or "À venir"
        lines.append(f"`{home} {hs} - {as_} {away}` — {status}")

if not lines:
    print("Aucun match aujourd'hui, rien envoyé.")
else:
    message = "📊 **Scores du jour**" + "\n".join(lines)
    r = requests.post(WEBHOOK, json={"content": message})
    print(f"Envoyé ! Status: {r.status_code}")
