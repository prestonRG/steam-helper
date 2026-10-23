# steam-helper

## Steam Game Finder

Run the graphical game browser with:

```powershell
python scripts\steam_ids_gui.py
```

The window lists installed Steam games, filters by name as you type (ignoring
capitalization, punctuation, and accents), and lets you copy a selected app ID.
Refreshing checks Steam Store metadata to exclude tools and other non-game apps,
so an internet connection is required.

The command-line listing and search remain available with
`python scripts\parse_steam_apps.py` and
`python scripts\parse_steam_apps.py --search "game name"`.
