import requests
import os
from datetime import datetime

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

LEAGUES = [
    {"name": "Premier League",    "id": "4328", "emoji": "🏴󠁧󁢥󁮧󁿢"},
    {"name": "La Liga",           "id": "4335", "emoji": "🇪🇸"},
    {"name": "Serie A",           "id": "4332", "emoji": "🇮🇹"},
    {"name": "Bundesliga",        "id": "4331", "emoji": "🇩🇪"},
    {"name": "Ligue 1",           "id": "4334", "emoji": "🇫🇷"},
    {"name": "MLS",               "id": "4346", "emoji": "🇺🇸"},
    {"name": "Brasileirao",       "id": "4351", "emoji": "🇧🇷"},
    {"name": "Liga MX",           "id": "4350", "emoji": "🇲🇽"},
    {"name": "Argentine Primera", "id": "4406", "emoji": "🇦🇷"},
    {"name": "Eredivisie",        "id": "4337", "emoji": "🇳🇱"},
]

MEDALS = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]

def fetch_leader(league):
    url = f"https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l={league['id']}&s=2024-2025"
    try:
        r = requests.get(url, timeout=10)
        table = r.json().get("table") or []
        if table:
            # Prend le 1er du classement
            top = table[0]
            return {
                "team": top.get("strTeam", "?"),
                "pts": top.get("intPoints", "?"),
                "league": league["name"],
                "emoji": league["emoji"],
            }
    except Exception as e:
        print(f"Erreur {league['name']}: {e}")
    return None

def send_embed(embed):
    r = requests.post(WEBHOOK, json={"embeds": [embed]})
    print(f"Discord: {r.status_code}")
    if r.status_code not in (200, 204):
        print(f"Erreur: {r.text}")

# ── Main ─────────────────────────────────────────────────────────────────────

print(f"=== Récap {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC ===")

leaders = []
for league in LEAGUES:
    result = fetch_leader(league)
    if result:
        leaders.append(result)
        print(f"✓ {league['name']} → {result['team']} ({result['pts']} pts)")
    else:
        print(f"✗ {league['name']} → aucune donnée")

if not leaders:
    requests.post(WEBHOOK, json={"content": "😴 Aucun classement disponible (hors saison)."})
    print("Aucun leader trouvé.")
else:
    # Trier par points décroissant
    leaders.sort(key=lambda x: int(x["pts"]) if str(x["pts"]).isdigit() else 0, reverse=True)

    lines = []
    for i, l in enumerate(leaders):
        medal = MEDALS[i] if i < len(MEDALS) else f"{i+1}."
        lines.append(f"{medal} {l['emoji']} **{l['team']}** — {l['pts']} pts  ·  *{l['league']}*")

    embed = {
        "title": "🌍  Leaders mondiaux du foot",
        "description": "\n".join(lines),
        "color": 0xf1c40f,
        "footer": {"text": f"⚽ Football Scores Bot  •  {datetime.utcnow().strftime('%d/%m/%Y')}"},
        "timestamp": datetime.utcnow().isoformat()
    }

    send_embed(embed)
    print(f"{len(leaders)} leaders envoyés")
