import requests
import os
import json
from datetime import datetime, timedelta

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = "last_sent.json"

LEAGUES = {
    "MLS": {"id": "4346", "emoji": "🇺🇸"},
    "Brasileirao": {"id": "4351", "emoji": "🇧🇷"},
    "Liga MX": {"id": "4350", "emoji": "🇲🇽"},
    "Argentine Primera": {"id": "4406", "emoji": "🇦🇷"},
    "Ligue 1": {"id": "4334", "emoji": "🇫🇷"},
    "Premier League": {"id": "4328", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "La Liga": {"id": "4335", "emoji": "🇪🇸"},
    "Serie A": {"id": "4332", "emoji": "🇮🇹"},
    "Bundesliga": {"id": "4331", "emoji": "🇩🇪"},
    "Eredivisie": {"id": "4337", "emoji": "🇳🇱"},
    "Champions League": {"id": "4480", "emoji": "⭐"},
    "Europa League": {"id": "4481", "emoji": "🔵"},
}

STATUS_MAP = {
    "FT": "✅ Terminé",
    "HT": "⏸️ Mi-temps",
    "NS": "🕐 À venir",
    "1H": "🔴 En cours — 1ère mi-temps",
    "2H": "🔴 En cours — 2ème mi-temps",
    "ET": "⚡ Prolongations",
    "PEN": "🎯 Tirs au but",
    "POSTP": "📅 Reporté",
    "CANC": "❌ Annulé",
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_matches(league_id, date_str):
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={date_str}&l={league_id}"
    try:
        r = requests.get(url, timeout=10)
        return r.json().get("events") or []
    except:
        return []

def get_status_label(m):
    raw = (m.get("strStatus") or "").upper()
    return STATUS_MAP.get(raw, f"🟡 {raw}" if raw else "🕐 À venir")

def build_score_embed(m, league_name, league_emoji):
    home = m["strHomeTeam"]
    away = m["strAwayTeam"]
    hs = m["intHomeScore"]
    as_ = m["intAwayScore"]
    status = get_status_label(m)
    thumb = m.get("strHomeTeamBadge") or None

    score_line = f"**{hs}  —  {as_}**"
    if int(hs) > int(as_):
        winner = f"🏆 {home} gagne !"
        color = 0x2ecc71
    elif int(as_) > int(hs):
        winner = f"🏆 {away} gagne !"
        color = 0x2ecc71
    else:
        winner = "🤝 Match nul"
        color = 0xf39c12

    embed = {
        "title": f"{league_emoji} {league_name}",
        "description": winner,
        "color": color,
        "fields": [
            {"name": f"🏠 {home}", "value": "\u200b", "inline": True},
            {"name": score_line, "value": status, "inline": True},
            {"name": f"✈️ {away}", "value": "\u200b", "inline": True},
        ],
        "footer": {
            "text": f"⚽ Football Scores Bot • {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"
        }
    }
    if thumb:
        embed["thumbnail"] = {"url": thumb}
    return embed

def build_reminder_embed(m, league_name, league_emoji, minutes_before):
    home = m["strHomeTeam"]
    away = m["strAwayTeam"]
    kickoff = m.get("strTime") or "?"
    thumb = m.get("strHomeTeamBadge") or None

    if minutes_before == 60:
        title = f"⏰ Dans 1 heure !"
        color = 0x3498db
    else:
        title = f"🚨 Dans 15 minutes !"
        color = 0xe74c3c

    embed = {
        "title": title,
        "description": f"{league_emoji} **{league_name}**",
        "color": color,
        "fields": [
            {"name": "🏠 Domicile", "value": home, "inline": True},
            {"name": "⚽ VS", "value": "\u200b", "inline": True},
            {"name": "✈️ Extérieur", "value": away, "inline": True},
            {"name": "🕐 Coup d'envoi", "value": f"`{kickoff} UTC`", "inline": False},
        ],
        "footer": {
            "text": f"⚽ Football Scores Bot • {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"
        }
    }
    if thumb:
        embed["thumbnail"] = {"url": thumb}
    return embed

def send_embeds_batch(embeds, header=None):
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i+10]
        payload = {"embeds": batch}
        if header and i == 0:
            payload["content"] = header
        requests.post(WEBHOOK, json=payload)

# ── Main ──────────────────────────────────────────────────────────────────────

state = load_state()
first_run = len(state) == 0
now_utc = datetime.utcnow()
today = now_utc.strftime("%Y-%m-%d")

score_embeds = []
reminder_embeds = []

if first_run:
    dates = [(now_utc - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    send_embeds_batch([], header="🚀 **Premier lancement — Envoi de l'historique des 30 derniers jours...**")
    print("Premier run — historique 30 jours")
else:
    dates = [today]
    print("Run normal")

for date_str in dates:
    for league_name, league_info in LEAGUES.items():
        matches = fetch_matches(league_info["id"], date_str)

        for m in matches:
            match_id = m.get("idEvent")
            current_score = f"{m['intHomeScore']}-{m['intAwayScore']}-{m.get('strStatus','')}"
            last = state.get(match_id)
            has_score = m["intHomeScore"] is not None

            # ── Scores ────────────────────────────────────────────────────────
            if first_run:
                if has_score:
                    score_embeds.append(build_score_embed(m, league_name, league_info["emoji"]))
                    state[match_id] = current_score
            else:
                if has_score and current_score != last:
                    score_embeds.append(build_score_embed(m, league_name, league_info["emoji"]))
                    state[match_id] = current_score

            # ── Rappels (seulement pour aujourd'hui, matchs pas encore commencés) ──
            if not first_run and date_str == today and not has_score:
                time_str = m.get("strTime") or ""
                if time_str:
                    try:
                        kickoff = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            kickoff = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M")
                        except:
                            kickoff = None

                    if kickoff:
                        diff = (kickoff - now_utc).total_seconds() / 60

                        reminder_key_60 = f"reminder_60_{match_id}"
                        reminder_key_15 = f"reminder_15_{match_id}"

                        if 55 <= diff <= 65 and not state.get(reminder_key_60):
                            reminder_embeds.append(build_reminder_embed(m, league_name, league_info["emoji"], 60))
                            state[reminder_key_60] = True

                        if 10 <= diff <= 20 and not state.get(reminder_key_15):
                            reminder_embeds.append(build_reminder_embed(m, league_name, league_info["emoji"], 15))
                            state[reminder_key_15] = True

# ── Envoi ─────────────────────────────────────────────────────────────────────

if reminder_embeds:
    send_embeds_batch(reminder_embeds, header="📣 **Rappel — Matchs à venir !**")
    print(f"{len(reminder_embeds)} rappels envoyés")

if score_embeds:
    header = "📅 **Historique des résultats**" if first_run else "📊 **Mise à jour des scores**"
    send_embeds_batch(score_embeds, header=header)
    print(f"{len(score_embeds)} scores envoyés")

if not score_embeds and not reminder_embeds:
    print("Rien de nouveau.")

save_state(state)
print("Done.")
