import requests
import os
import json
from datetime import datetime, timedelta

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = "last_sent.json"

LEAGUES = {
    "MLS":               {"id": "4346", "emoji": "🇺🇸"},
    "Brasileirao":       {"id": "4351", "emoji": "🇧🇷"},
    "Liga MX":           {"id": "4350", "emoji": "🇲🇽"},
    "Argentine Primera": {"id": "4406", "emoji": "🇦🇷"},
    "Ligue 1":           {"id": "4334", "emoji": "🇫🇷"},
    "Premier League":    {"id": "4328", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "La Liga":           {"id": "4335", "emoji": "🇪🇸"},
    "Serie A":           {"id": "4332", "emoji": "🇮🇹"},
    "Bundesliga":        {"id": "4331", "emoji": "🇩🇪"},
    "Eredivisie":        {"id": "4337", "emoji": "🇳🇱"},
    "Champions League":  {"id": "4480", "emoji": "⭐"},
    "Europa League":     {"id": "4481", "emoji": "🔵"},
}

STATUS_MAP = {
    "FT":    ("✅ Terminé",        0x2ecc71),
    "HT":    ("⏸️ Mi-temps",       0xf39c12),
    "1H":    ("🔴 1ère mi-temps",  0xe74c3c),
    "2H":    ("🔴 2ème mi-temps",  0xe74c3c),
    "ET":    ("⚡ Prolongations",   0x9b59b6),
    "PEN":   ("🎯 Tirs au but",    0x9b59b6),
    "POSTP": ("📅 Reporté",        0x7f8c8d),
    "CANC":  ("❌ Annulé",        0x7f8c8d),
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
    except Exception as e:
        print(f"Erreur fetch {league_id} {date_str}: {e}")
        return []

def build_score_embed(m, league_name, league_emoji):
    home = m["strHomeTeam"]
    away = m["strAwayTeam"]
    hs = int(m["intHomeScore"])
    as_ = int(m["intAwayScore"])
    raw_status = (m.get("strStatus") or "FT").upper()
    status_label, color = STATUS_MAP.get(raw_status, ("🟡 " + raw_status, 0x95a5a6))
    home_badge = m.get("strHomeTeamBadge") or ""

    if hs > as_:
        home_display = f"**{home}** 🏆"
        away_display = away
        winner_line = f"🏆 **{home}** remporte le match !"
    elif as_ > hs:
        home_display = home
        away_display = f"**{away}** 🏆"
        winner_line = f"🏆 **{away}** remporte le match !"
    else:
        home_display = f"**{home}**"
        away_display = f"**{away}**"
        winner_line = "🤝 Match nul"

    date_val = m.get("dateEvent") or ""
    time_val = (m.get("strTime") or "")[:5]
    time_display = f"{date_val} — {time_val} UTC" if date_val and time_val else date_val

    description = "\n".join(filter(None, [
        f"🏠 {home_display}",
        f"# {hs}  —  {as_}",
        f"✈️ {away_display}",
        "",
        f"{status_label}  •  {winner_line}",
        f"🗓 {time_display}" if time_display else "",
    ]))

    embed = {
        "title": f"{league_emoji}  {league_name}",
        "description": description,
        "color": color,
        "footer": {"text": f"⚽ Football Scores Bot  •  {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"}
    }
    if home_badge:
        embed["thumbnail"] = {"url": home_badge}
    return embed

def build_reminder_embed(m, league_name, league_emoji, hours_before):
    home = m["strHomeTeam"]
    away = m["strAwayTeam"]
    time_val = (m.get("strTime") or "?")[:5]
    date_val = m.get("dateEvent") or ""
    home_badge = m.get("strHomeTeamBadge") or ""

    if hours_before == 2:
        title = "⏰ Dans 2 heures !"
        color = 0x3498db
    elif hours_before == 1:
        title = "🟠 Dans 1 heure !"
        color = 0xe67e22
    else:
        title = "🚨 Dans 15 minutes !"
        color = 0xe74c3c

    description = "\n".join(filter(None, [
        f"{league_emoji}  **{league_name}**",
        "",
        f"🏠 **{home}**",
        "**VS**",
        f"✈️ **{away}**",
        "",
        f"🗓 {date_val} — {time_val} UTC",
    ]))

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": f"⚽ Football Scores Bot  •  {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"}
    }
    if home_badge:
        embed["thumbnail"] = {"url": home_badge}
    return embed

def send_embeds_batch(embeds, header=None):
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i+10]
        payload = {"embeds": batch}
        if header and i == 0:
            payload["content"] = header
        r = requests.post(WEBHOOK, json=payload)
        if r.status_code not in (200, 204):
            print(f"Erreur Discord: {r.status_code} — {r.text[:200]}")

# ── Main ──────────────────────────────────────────────────────────────────────

state = load_state()
first_run = len(state) == 0
now_utc = datetime.utcnow()
today = now_utc.strftime("%Y-%m-%d")

print(f"=== {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC — first_run={first_run} ===")

score_embeds = []
reminder_embeds = []

if first_run:
    dates = [(now_utc - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    send_embeds_batch([], header="🚀 **Premier lancement — Historique des 30 derniers jours...**")
else:
    dates = [today]

for date_str in dates:
    for league_name, league_info in LEAGUES.items():
        matches = fetch_matches(league_info["id"], date_str)
        for m in matches:
            match_id = m.get("idEvent")
            hs = m["intHomeScore"]
            as_ = m["intAwayScore"]
            current_score = f"{hs}-{as_}-{m.get('strStatus','')}"
            last = state.get(match_id)
            has_score = hs is not None

            if first_run:
                if has_score:
                    score_embeds.append(build_score_embed(m, league_name, league_info["emoji"]))
                    state[match_id] = current_score
            else:
                if has_score and current_score != last:
                    print(f"Nouveau score : {m['strHomeTeam']} {hs}-{as_} {m['strAwayTeam']} ({league_name})")
                    send_embeds_batch(
                        [build_score_embed(m, league_name, league_info["emoji"])],
                        header="📊 **Nouveau résultat !**"
                    )
                    state[match_id] = current_score

            # Rappels 2h / 1h / 15min
            if not first_run and date_str == today and not has_score:
                time_str = m.get("strTime") or ""
                if time_str:
                    kickoff = None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                        try:
                            kickoff = datetime.strptime(f"{today} {time_str}", fmt)
                            break
                        except:
                            pass
                    if kickoff:
                        diff = (kickoff - now_utc).total_seconds() / 60
                        print(f"Match dans {diff:.0f} min : {m['strHomeTeam']} vs {m['strAwayTeam']}")
                        for key_prefix, low, high, h in [
                            ("r120", 115, 125, 2),
                            ("r60",   55,  65, 1),
                            ("r15",   10,  20, 0),
                        ]:
                            key = f"{key_prefix}_{match_id}"
                            if low <= diff <= high and not state.get(key):
                                print(f"→ Rappel {h}h envoyé !")
                                reminder_embeds.append(build_reminder_embed(m, league_name, league_info["emoji"], h))
                                state[key] = True

if first_run and score_embeds:
    send_embeds_batch(score_embeds, header="📅 **Historique des résultats**")
    print(f"{len(score_embeds)} scores historique envoyés")

if reminder_embeds:
    send_embeds_batch(reminder_embeds, header="📣 **Rappel — Match imminent !**")
    print(f"{len(reminder_embeds)} rappels envoyés")

if not first_run and not score_embeds and not reminder_embeds:
    print("Rien de nouveau.")

save_state(state)
print("Done.")
