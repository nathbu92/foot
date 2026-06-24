import requests
import os
from datetime import datetime

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

LEAGUES = {
    "Premier League":    {"id": "4328", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "La Liga":           {"id": "4335", "emoji": "🇪🇸"},
    "Serie A":           {"id": "4332", "emoji": "🇮🇹"},
    "Bundesliga":        {"id": "4331", "emoji": "🇩🇪"},
    "Ligue 1":           {"id": "4334", "emoji": "🇫🇷"},
    "MLS":               {"id": "4346", "emoji": "🇺🇸"},
    "Brasileirao":       {"id": "4351", "emoji": "🇧🇷"},
    "Liga MX":           {"id": "4350", "emoji": "🇲🇽"},
    "Argentine Primera": {"id": "4406", "emoji": "🇦🇷"},
    "Eredivisie":        {"id": "4337", "emoji": "🇳🇱"},
}

def fetch_standings(league_id):
    url = f"https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l={league_id}&s=2024-2025"
    try:
        r = requests.get(url, timeout=10)
        return r.json().get("table") or []
    except:
        return []

def build_standings_embed(league_name, league_emoji, table):
    lines = ["```"]
    lines.append(f"{'#':<3} {'Équipe':<22} {'Pts':>4}")
    lines.append("─" * 30)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for row in table[:5]:
        pos = int(row.get("intRank", 0))
        team = (row.get("strTeam") or "?")[:20]
        pts = row.get("intPoints", "-")
        medal = medals.get(pos, f"{pos}. ")
        lines.append(f"{medal:<3} {team:<22} {pts:>4} pts")

    lines.append("```")

    return {
        "title": f"{league_emoji}  {league_name}",
        "description": "\n".join(lines),
        "color": 0xf1c40f,  # doré
        "footer": {"text": f"⚽ Football Scores Bot  •  Top 5  •  {datetime.utcnow().strftime('%d/%m/%Y')}"}
    }

def send_embeds_batch(embeds, header=None):
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i+10]
        payload = {"embeds": batch}
        if header and i == 0:
            payload["content"] = header
        requests.post(WEBHOOK, json=payload)

# ── Main ─────────────────────────────────────────────────────────────────────

embeds = []
for league_name, league_info in LEAGUES.items():
    table = fetch_standings(league_info["id"])
    if table:
        embeds.append(build_standings_embed(league_name, league_info["emoji"], table))
        print(f"✓ {league_name}")
    else:
        print(f"✗ {league_name} — pas de données")

if embeds:
    send_embeds_batch(embeds, header=f"☀️ **Bonjour ! Classements du {datetime.utcnow().strftime('%d/%m/%Y')} :**")
    print(f"{len(embeds)} classements envoyés")
else:
    requests.post(WEBHOOK, json={"content": "😴 Aucun classement disponible aujourd'hui."})
