# Topbins

Live football scores in your macOS menubar. Free, no API key, no subscription.

**Data:** ESPN public API  
**Leagues:** Premier League · La Liga · Bundesliga · Serie A · Ligue 1 · UCL · World Cup

![menubar screenshot placeholder](screenshot.png)

---

## Install (pre-built app)

1. Download `Topbins.app` from [Releases](../../releases)
2. Drag it to `/Applications`
3. Open it — allow it in System Settings → Privacy & Security if prompted
4. The ⚽ icon appears in your menubar

> macOS may show a security warning the first time since the app isn't notarized.  
> To bypass: right-click the app → Open → Open anyway.

---

## Settings

Click the ⚽ icon → **⚙ Settings**

| Setting | Options |
|---|---|
| Leagues | Toggle any league on/off — only enabled leagues hit the API |
| Refresh Rate | 15s · 30s · 1 min · 5 min · 10 min |

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

- One API call per enabled league, on each refresh tick
- Scores update automatically; force-refresh anytime from the menu
- Settings persist across restarts

---

## License

MIT
