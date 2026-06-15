#!/usr/bin/env python3
"""
Topbins — macOS menubar app
Data: ESPN public API | No API key required
"""

import copy
import json
import os
import threading
import urllib.request
from datetime import datetime, timezone

import rumps
from AppKit import (
    NSMutableAttributedString, NSMutableParagraphStyle, NSTextTab,
    NSParagraphStyleAttributeName, NSForegroundColorAttributeName,
    NSColor, NSFont, NSFontAttributeName, NSView,
)
from Foundation import NSString

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

SETTINGS_PATH = os.path.expanduser("~/.config/topbins/settings.json")

# Set to True to inject a fake live match for testing extra stats
DEBUG_MOCK = False

MOCK_EVENT = {
    "league": "World Cup",
    "home": "ENG", "away": "BRA",
    "hflag": "🇬🇧", "aflag": "🇧🇷",
    "hscore": "1", "ascore": "1",
    "state": "in", "detail": "67'",
    "venue": "BC Place",
    "city": "Vancouver, British Columbia",
    "country_flag": "🇨🇦",
    "home_stats": {
        "possessionPct": "54.3", "totalShots": "12",
        "shotsOnTarget": "5", "wonCorners": "6", "foulsCommitted": "8",
    },
    "away_stats": {
        "possessionPct": "45.7", "totalShots": "9",
        "shotsOnTarget": "3", "wonCorners": "3", "foulsCommitted": "11",
    },
}

DEFAULT_SETTINGS = {
    "leagues":         {lbl: (lbl == "World Cup") for _, lbl in ALL_LEAGUES},
    "refresh_seconds":  60,
    "extra_stats":      True,
    "show_locations":   False,
}

EXTRA_STATS = [
    ("possessionPct",  "Possession"),
    ("totalShots",     "Shots"),
    ("shotsOnTarget",  "On Target"),
    ("wonCorners",     "Corners"),
    ("foulsCommitted", "Fouls"),
]

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

# ─── Venue ────────────────────────────────────────────────────────────────────

_COUNTRY_FLAGS = {
    "USA": "🇺🇸", "Canada": "🇨🇦", "Mexico": "🇲🇽",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Germany": "🇩🇪", "France": "🇫🇷",
    "Spain": "🇪🇸", "Italy": "🇮🇹", "Netherlands": "🇳🇱",
    "Portugal": "🇵🇹", "Brazil": "🇧🇷", "Argentina": "🇦🇷",
    "Australia": "🇦🇺", "Japan": "🇯🇵", "South Korea": "🇰🇷",
    "Morocco": "🇲🇦", "Saudi Arabia": "🇸🇦", "Qatar": "🇶🇦",
    "UAE": "🇦🇪", "Switzerland": "🇨🇭", "Belgium": "🇧🇪",
    "Turkey": "🇹🇷", "Greece": "🇬🇷", "Poland": "🇵🇱",
}

def _spacer_item():
    view = NSView.alloc().initWithFrame_(((0, 0), (1, 5)))  # 5px tall custom view
    item = rumps.MenuItem("")
    item._menuitem.setView_(view)
    item._menuitem.setEnabled_(False)
    return item

def _venue_item(city, country_flag):
    short_city = city.split(",")[0].strip()
    text = f"     📍 {short_city}"
    attrs = {
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
        NSFontAttributeName: NSFont.systemFontOfSize_(11),
    }
    attr_str = NSMutableAttributedString.alloc().initWithString_attributes_(text, attrs)
    item = rumps.MenuItem("")
    item._menuitem.setAttributedTitle_(attr_str)
    item._menuitem.setEnabled_(False)
    return item

# ─── ESPN API ─────────────────────────────────────────────────────────────────

def _local_time(utc_str):
    try:
        utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        local_dt = utc_dt.astimezone()
        return local_dt.strftime("%-I:%M %p")
    except Exception:
        return "TBD"

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
        state = st.get("state", "")
        detail = st.get("shortDetail", "")
        if state == "pre":
            detail = _local_time(event.get("date", ""))
        def stats_dict(side):
            return {s["name"]: s["displayValue"] for s in side.get("statistics", [])}

        venue_obj = comp.get("venue", {})
        addr = venue_obj.get("address", {})
        city = addr.get("city", "")
        country = addr.get("country", "")
        country_flag = _COUNTRY_FLAGS.get(country, "")

        events.append({
            "league":      label,
            "home":        ha,
            "away":        aa,
            "hflag":       get_flag(ha, label),
            "aflag":       get_flag(aa, label),
            "hscore":      home.get("score", ""),
            "ascore":      away.get("score", ""),
            "state":       state,
            "detail":      detail,
            "home_stats":  stats_dict(home),
            "away_stats":  stats_dict(away),
            "city":        city,
            "country_flag": country_flag,
        })
    return events

# ─── Formatters ───────────────────────────────────────────────────────────────

def fmt_score(m):
    return f"{m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}  {m['detail']}"

def fmt_fixture(m):
    return f"{m['hflag']}{m['home']} vs {m['aflag']}{m['away']}  {m['detail']}"

def fmt_result(m):
    return f"{m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}"

_MENU_FONT   = None  # lazily initialised
_MENU_PADDING = 44   # macOS menu left/right chrome

def _text_width(text):
    global _MENU_FONT
    if _MENU_FONT is None:
        _MENU_FONT = NSFont.menuFontOfSize_(0)
    return NSString.stringWithString_(text).sizeWithAttributes_(
        {NSFontAttributeName: _MENU_FONT}
    ).width

def _calc_tabs(events, show_loc):
    """Measure the widest row to estimate menu width, return dynamic tab stops."""
    max_team_w = 80
    max_total_w = 80

    for m in events:
        if m["state"] not in ("pre", "post"):
            continue
        if m["state"] == "pre":
            team = f"  {m['hflag']}{m['home']} vs {m['aflag']}{m['away']}"
        else:
            team = f"  {m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}"
        tw = _text_width(team)
        max_team_w = max(max_team_w, tw)

        if show_loc and m.get("city"):
            city = m["city"].split(",")[0].strip()
            total = _text_width(f"{team}  {m['detail']}  📍 {city}")
        else:
            total = _text_width(f"{team}  {m['detail']}")
        max_total_w = max(max_total_w, total)

    menu_w = max_total_w + _MENU_PADDING

    # Stats table: home centered at 42%, away at 72% of menu width
    stats_tabs = (int(menu_w * 0.42), int(menu_w * 0.72))

    # Match rows: time centered just after team string, location left-aligned after that
    if show_loc:
        match_tabs = (int(max_team_w + 40), int(max_team_w + 100))
    else:
        match_tabs = (int(max_team_w + 40),)

    return stats_tabs, match_tabs

def _table_item(text, muted=False, tab_stops=(125, 185), alignments=(2, 2)):
    """NSMenuItem with attributed string for pixel-perfect tab-stop alignment.
    alignment: 0=left, 1=right, 2=center per column."""
    para = NSMutableParagraphStyle.new()
    stops = []
    for i, pos in enumerate(tab_stops):
        align = alignments[i] if i < len(alignments) else 2
        stops.append(NSTextTab.alloc().initWithType_location_(align, pos))
    para.setTabStops_(stops)
    attrs = {NSParagraphStyleAttributeName: para}
    if muted:
        attrs[NSForegroundColorAttributeName] = NSColor.secondaryLabelColor()
    attr_str = NSMutableAttributedString.alloc().initWithString_attributes_(text, attrs)
    item = rumps.MenuItem("")
    item._menuitem.setAttributedTitle_(attr_str)
    item._menuitem.setEnabled_(False)
    return item

def stat_table_items(m, tab_stops=(125, 185)):
    items = []
    for key, label in EXTRA_STATS:
        hv = m["home_stats"].get(key, "-")
        av = m["away_stats"].get(key, "-")
        items.append(_table_item(f"  {label}\t{hv}\t{av}", tab_stops=tab_stops))
    return items

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
            s = copy.deepcopy(DEFAULT_SETTINGS)
            self._write_settings(s)
            return s

    def _write_settings(self, s):
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(s, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SETTINGS_PATH)

    def _save_settings(self):
        self._write_settings(self.settings)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _fetch(self):
        active = [(slug, lbl) for slug, lbl in ALL_LEAGUES
                  if self.settings["leagues"].get(lbl, False)]
        events = []
        for slug, lbl in active:
            events.extend(parse_events(fetch_league(slug), lbl))
        if DEBUG_MOCK:
            events.insert(0, MOCK_EVENT)
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

        extra    = self.settings.get("extra_stats", False)
        show_loc = self.settings.get("show_locations", False)
        tabs, mtabs = _calc_tabs(events, show_loc)

        def maybe_venue(m):
            if show_loc and m.get("city"):
                items.append(_venue_item(m["city"], m.get("country_flag", "")))

        if live:
            first = live[0]
            if show_loc and first.get("city"):
                short_city = first["city"].split(",")[0].strip()
                add(f"🟢  LIVE    📍 {short_city}")
            else:
                add("🟢  LIVE")
            for m in live:
                if extra:
                    if show_loc:
                        items.append(_table_item("", muted=True, tab_stops=tabs))
                    items.append(_table_item(
                        f"  \t{m['hflag']}{m['home']}\t{m['aflag']}{m['away']}",
                        muted=True, tab_stops=tabs,
                    ))
                    items.append(_table_item(
                        f"  Score\t{m['hscore']}\t{m['ascore']}",
                        tab_stops=tabs,
                    ))
                    for table_item in stat_table_items(m, tab_stops=tabs):
                        items.append(table_item)
                else:
                    add(f"     {fmt_score(m)}")
            sep()


        def match_row(match_str, detail, city):
            if show_loc and city:
                loc = f"📍 {city.split(',')[0].strip()}"
                return _table_item(f"  {match_str}\t{detail}\t{loc}", tab_stops=mtabs, alignments=(2, 0))
            else:
                return _table_item(f"  {match_str}\t{detail}", tab_stops=mtabs, alignments=(2,))

        if upcoming:
            add("🕐  UPCOMING")
            for i, m in enumerate(upcoming):
                items.append(match_row(
                    f"{m['hflag']}{m['home']} vs {m['aflag']}{m['away']}",
                    m["detail"], m.get("city", ""),
                ))
                if show_loc and i < len(upcoming) - 1:
                    items.append(_spacer_item())
            sep()

        if finished:
            add("✅  FINISHED")
            for i, m in enumerate(finished):
                items.append(match_row(
                    f"{m['hflag']}{m['home']} {m['hscore']}-{m['ascore']} {m['aflag']}{m['away']}",
                    "FT", m.get("city", ""),
                ))
                if show_loc and i < len(finished) - 1:
                    items.append(_spacer_item())
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

        extra_stats_item = rumps.MenuItem("Extra Stats", callback=self._toggle_extra_stats)
        extra_stats_item.state = 1 if self.settings.get("extra_stats", False) else 0
        settings.add(extra_stats_item)

        locations_item = rumps.MenuItem("Show Locations", callback=self._toggle_locations)
        locations_item.state = 1 if self.settings.get("show_locations", False) else 0
        settings.add(locations_item)

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

    def _toggle_locations(self, sender):
        self.settings["show_locations"] = not self.settings.get("show_locations", False)
        self._save_settings()
        with self._lock:
            events = list(self._events)
        self._redraw(events)

    def _toggle_extra_stats(self, sender):
        self.settings["extra_stats"] = not self.settings.get("extra_stats", False)
        self._save_settings()
        with self._lock:
            events = list(self._events)
        self._redraw(events)

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
