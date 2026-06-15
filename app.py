#!/usr/bin/env python3
"""
Football Scores — macOS menubar app
Data: ESPN public API | No API key required
"""

import copy
import json
import os
import threading
import urllib.request

import rumps

# ─── Config ───────────────────────────────────────────────────────────────────

ALL_LEAGUES = [
    ("eng.1",          "Premier League"),
    ("esp.1",          "La Liga"),
    ("ger.1",          "Bundesliga"),
    ("ita.1",          "Serie A"),
    ("fra.1",          "Ligue 1"),
    ("uefa.champions", "UCL"),
    ("FIFA.World",     "World Cup"),
]

REFRESH_OPTIONS = [
    (15,  "15 seconds"),
    (30,  "30 seconds"),
    (60,  "1 minute"),
    (300, "5 minutes"),
    (600, "10 minutes"),
]

SETTINGS_PATH = os.path.expanduser("~/.config/football-scores/settings.json")

DEFAULT_SETTINGS = {
    "leagues":         {lbl: (lbl == "World Cup") for _, lbl in ALL_LEAGUES},
    "refresh_seconds": 60,
}

# ─── Flags ────────────────────────────────────────────────────────────────────

def _flag(iso2):
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())

_FIFA_ISO2 = {
    "AFG":"AF","ALB":"AL","ALG":"DZ","ANG":"AO","ARG":"AR","ARM":"AM",
    "AUS":"AU","AUT":"AT","AZE":"AZ","BAN":"BD","BEL":"BE","BIH":"BA",
    "BOL":"BO","BRA":"BR","BUL":"BG","CMR":"CM","CAN":"CA","CHI":"CL",
    "CHN":"CN","CIV":"CI","COL":"CO","CPV":"CV","CRC":"CR","CRO":"HR",
    "CUB":"CU","CYP":"CY","CZE":"CZ","DEN":"DK","DOM":"DO","ECU":"EC",
    "EGY":"EG","ENG":"GB","ESP":"ES","EST":"EE","ETH":"ET","FIN":"FI",
    "FRA":"FR","FRO":"FO","GEO":"GE","GER":"DE","GHA":"GH","GRE":"GR",
    "GUA":"GT","GUI":"GN","HAI":"HT","HON":"HN","HUN":"HU","IDN":"ID",
    "IND":"IN","IRL":"IE","IRN":"IR","IRQ":"IQ","ISL":"IS","ISR":"IL",
    "ITA":"IT","JAM":"JM","JOR":"JO","JPN":"JP","KAZ":"KZ","KEN":"KE",
    "KOR":"KR","KSA":"SA","KUW":"KW","LAT":"LV","LBN":"LB","LIE":"LI",
    "LTU":"LT","LUX":"LU","MAR":"MA","MAS":"MY","MEX":"MX","MDA":"MD",
    "MKD":"MK","MLI":"ML","MLT":"MT","MNE":"ME","MOZ":"MZ","NCA":"NI",
    "NED":"NL","NGA":"NG","NIR":"GB","NOR":"NO","NZL":"NZ","OMA":"OM",
    "PAK":"PK","PAL":"PS","PAN":"PA","PAR":"PY","PER":"PE","PHI":"PH",
    "POL":"PL","POR":"PT","QAT":"QA","ROM":"RO","RSA":"ZA","RUS":"RU",
    "RWA":"RW","SCO":"GB","SEN":"SN","SIN":"SG","SLO":"SI","SLV":"SV",
    "SRB":"RS","SUI":"CH","SVK":"SK","SWE":"SE","SYR":"SY","TAN":"TZ",
    "THA":"TH","TRI":"TT","TUN":"TN","TUR":"TR","UAE":"AE","UGA":"UG",
    "UKR":"UA","URU":"UY","USA":"US","UZB":"UZ","VEN":"VE","VIE":"VN",
    "WAL":"GB","YEM":"YE","ZAM":"ZM","ZIM":"ZW",
}

_CLUB_ISO2 = {
    # Premier League
    "ARS":"GB","AVL":"GB","BHA":"GB","BOU":"GB","BRE":"GB","BUR":"GB",
    "CHE":"GB","CRY":"GB","EVE":"GB","FUL":"GB","LEE":"GB","LIV":"GB",
    "MAN":"GB","MNC":"GB","NEW":"GB","NFO":"GB","SHU":"GB","SUN":"GB",
    "TOT":"GB","WHU":"GB","WOL":"GB",
    # La Liga
    "ALA":"ES","ALV":"ES","ATM":"ES","BAR":"ES","BET":"ES","CAD":"ES",
    "GET":"ES","GIR":"ES","GRA":"ES","MAL":"ES","REA":"ES","RMA":"ES",
    "SEV":"ES","SOC":"ES","VAL":"ES","VIL":"ES",
    # Bundesliga
    "B04":"DE","BAY":"DE","BMG":"DE","DOR":"DE","FCA":"DE","FCU":"DE",
    "HDH":"DE","HSV":"DE","KOE":"DE","LEV":"DE","M05":"DE","MUN":"DE",
    "RBL":"DE","SCF":"DE","SGE":"DE","STP":"DE","SVW":"DE","TSG":"DE",
    "VFB":"DE","WOB":"DE",
    # Serie A
    "ATA":"IT","BOL":"IT","CAG":"IT","COMO":"IT","FIO":"IT","FRO":"IT",
    "GEN":"IT","INT":"IT","JUV":"IT","LAZ":"IT","LEC":"IT","MIL":"IT",
    "NAP":"IT","PAR":"IT","ROM":"IT","SAS":"IT","TOR":"IT","UDI":"IT",
    "VEN":"IT",
    # Ligue 1
    "ANG":"FR","AUX":"FR","HAC":"FR","LILL":"FR","LOR":"FR","LYON":"FR",
    "MNS":"FR","MON":"MC","NICE":"FR","NIC":"FR","OLM":"FR","PSG":"FR",
    "RCL":"FR","REN":"FR","STR":"FR","TOU":"FR","TRY":"FR",
    # UCL extras
    "AJX":"NL","BEN":"PT","BES":"TR","DYN":"UA","FEN":"TR","FEY":"NL",
    "GAL":"TR","PSV":"NL","SCP":"PT","SHK":"UA",
}

_LEAGUE_ISO2 = {
    "Premier League": "GB",
    "La Liga":        "ES",
    "Bundesliga":     "DE",
    "Serie A":        "IT",
    "Ligue 1":        "FR",
}

def get_flag(abbr, league):
    if league == "World Cup":
        iso2 = _FIFA_ISO2.get(abbr)
    else:
        iso2 = _CLUB_ISO2.get(abbr) or _LEAGUE_ISO2.get(league)
    return _flag(iso2) if iso2 else ""

# ─── ESPN API ─────────────────────────────────────────────────────────────────

def fetch_league(slug):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r)
    except Exception:
        return {}

def parse_events(data, label):
    events = []
    for event in data.get("events", []):
        comp  = event["competitions"][0]
        sides = {t["homeAway"]: t for t in comp["competitors"]}
        home  = sides.get("home", {})
        away  = sides.get("away", {})
        st    = comp["status"]["type"]
        ha    = home.get("team", {}).get("abbreviation", "?")
        aa    = away.get("team", {}).get("abbreviation", "?")
        events.append({
            "league": label,
            "home":   ha,
            "away":   aa,
            "hflag":  get_flag(ha, label),
            "aflag":  get_flag(aa, label),
            "hscore": home.get("score", ""),
            "ascore": away.get("score", ""),
            "state":  st.get("state", ""),
            "detail": st.get("shortDetail", ""),
        })
    return events

# ─── Formatters ───────────────────────────────────────────────────────────────

def fmt_score(m):
    return f"{m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}  {m['detail']}"

def fmt_fixture(m):
    return f"{m['hflag']}{m['home']} vs {m['aflag']}{m['away']}  {m['detail']}"

def fmt_result(m):
    return f"{m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}"

# ─── App ──────────────────────────────────────────────────────────────────────

class FootballApp(rumps.App):

    def __init__(self):
        super().__init__("⚽", quit_button=None)
        self.settings = self._load_settings()
        self._lock    = threading.Lock()
        self._events  = []
        self._dirty   = False

        # 0.5s timer to flush UI updates on main thread
        self._ui_timer = rumps.Timer(self._flush, 0.5)
        self._ui_timer.start()

        # Data refresh timer
        self._fetch_timer = rumps.Timer(
            lambda _: threading.Thread(target=self._fetch, daemon=True).start(),
            self.settings["refresh_seconds"],
        )
        self._fetch_timer.start()

        self._redraw([])
        threading.Thread(target=self._fetch, daemon=True).start()

    # ── Settings ──────────────────────────────────────────────────────────────

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH) as f:
                s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                s.setdefault(k, v)
            return s
        except Exception:
            return copy.deepcopy(DEFAULT_SETTINGS)

    def _save_settings(self):
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(self.settings, f, indent=2)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _fetch(self):
        active = [(slug, lbl) for slug, lbl in ALL_LEAGUES
                  if self.settings["leagues"].get(lbl, False)]
        events = []
        for slug, lbl in active:
            events.extend(parse_events(fetch_league(slug), lbl))
        with self._lock:
            self._events = events
        self._dirty = True

    def _flush(self, _):
        if self._dirty:
            self._dirty = False
            with self._lock:
                events = list(self._events)
            self._redraw(events)

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _redraw(self, events):
        live     = [e for e in events if e["state"] == "in"]
        upcoming = [e for e in events if e["state"] == "pre"]
        finished = [e for e in events if e["state"] == "post"]

        # Menubar title
        if live:
            self.title = fmt_score(live[0])
        elif upcoming:
            m = upcoming[0]
            self.title = f"{m['hflag']}{m['home']} vs {m['aflag']}{m['away']}"
        else:
            self.title = "⚽"

        items = []

        def sep():
            items.append(None)

        def add(title, callback=None):
            items.append(rumps.MenuItem(title, callback=callback))

        if live:
            add("🟢  LIVE")
            for m in live:
                add(f"     {fmt_score(m)}")
            sep()

        if upcoming:
            add("🕐  UPCOMING")
            for m in upcoming:
                add(f"     {fmt_fixture(m)}")
            sep()

        if finished:
            add("✅  FINISHED")
            for m in finished:
                add(f"     {fmt_result(m)}")
            sep()

        if not events:
            add("No matches today")
            sep()

        add("↺  Refresh Now", callback=self._on_refresh)
        sep()

        # ── Settings submenu ──────────────────────────────────────────────────
        settings = rumps.MenuItem("⚙  Settings")

        leagues_menu = rumps.MenuItem("Leagues")
        for _, lbl in ALL_LEAGUES:
            item = rumps.MenuItem(lbl, callback=self._toggle_league)
            item.state = 1 if self.settings["leagues"].get(lbl, False) else 0
            leagues_menu.add(item)
        settings.add(leagues_menu)

        rate_menu = rumps.MenuItem("Refresh Rate")
        for secs, lbl in REFRESH_OPTIONS:
            item = rumps.MenuItem(lbl, callback=self._set_refresh_rate)
            item.state = 1 if secs == self.settings["refresh_seconds"] else 0
            rate_menu.add(item)
        settings.add(rate_menu)

        items.append(settings)
        sep()
        add("Quit", callback=lambda _: rumps.quit_application())

        # Swap menu
        self.menu.clear()
        for item in items:
            self.menu.add(rumps.separator if item is None else item)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_refresh(self, _):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _toggle_league(self, sender):
        lbl = sender.title
        self.settings["leagues"][lbl] = not self.settings["leagues"].get(lbl, False)
        self._save_settings()
        threading.Thread(target=self._fetch, daemon=True).start()

    def _set_refresh_rate(self, sender):
        secs = next((s for s, l in REFRESH_OPTIONS if l == sender.title), 60)
        self.settings["refresh_seconds"] = secs
        self._save_settings()
        self._fetch_timer.stop()
        self._fetch_timer = rumps.Timer(
            lambda _: threading.Thread(target=self._fetch, daemon=True).start(),
            secs,
        )
        self._fetch_timer.start()


if __name__ == "__main__":
    FootballApp().run()
