# Topbins

Live football scores in your macOS menubar. Free, no API key, no subscription.

<div align="center">

<a href="https://github.com/yasharya1/topbins/releases/latest/download/Topbins.zip">
  <img src="assets/download.svg" width="600"/>
</a>

</div>

**Data:** ESPN public API  
**Leagues:** Premier League · La Liga · Bundesliga · Serie A · Ligue 1 · UCL · World Cup

---

## Install

1. Download `Topbins.zip` from [Releases](../../releases/latest)
2. Unzip it — `Topbins.app` appears
3. Drag `Topbins.app` to `/Applications`
4. Open it — the ⚽ icon appears in your menubar

---

## Settings

Click the ⚽ icon → **⚙ Settings**

| Setting | Default | Description |
|---|---|---|
| Leagues | World Cup only | Toggle any league on/off — only enabled leagues hit the API |
| Refresh Rate | 1 minute | How often scores update (15s · 30s · 1 min · 5 min · 10 min) |
| Extra Stats | On | Live match stats table: possession, shots, on target, corners, fouls |
| Show Locations | Off | Adds venue city to each match row |
| Dunder Mifflin Mode | Off | Disguises live scores as office activity — `26' Emails \| 00 Calls` instead of the real scoreline. Popup panel unchanged. |

Settings are saved automatically to `~/.config/topbins/settings.json`.

---

## Build from source

**Requirements:** macOS, Python 3.9+

```bash
git clone https://github.com/yasharya1/topbins
cd topbins
pip install -r requirements.txt
python app.py
```

**Package as .app:**

```bash
pip install py2app
python setup.py py2app
# Output: dist/Topbins.app
```

---

## How it works

- One API call per enabled league on each refresh tick — disable unused leagues to reduce requests
- ESPN's scoreboard API updates every ~13 seconds; refreshing faster than that returns cached data
- Settings write atomically — no risk of corruption if the app is force-quit
- Scores update automatically; force-refresh anytime via **↺ Refresh Now**

---

## License

MIT
