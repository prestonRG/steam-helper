# Print installed Steam games and their app IDs on Windows and Linux.
import argparse
import json
import os
import re
import unicodedata
import warnings
from pathlib import Path
from urllib.request import urlopen


def steam_roots():
	# Return existing, commonly used Steam installation directories.
	home = Path.home()
	candidates = [
		home / ".steam" / "steam",
		home / ".steam" / "root",
		home / ".local" / "share" / "Steam",
		home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
	]

	for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA", "APPDATA"):
		base = os.environ.get(variable)
		if base:
			candidates.append(Path(base) / "Steam")

	return {path for path in candidates if path.is_dir()}


def steam_libraries(roots):
	# Find extra library folders listed in libraryfolders.vdf.
	libraries = set(roots)
	path_entry = re.compile(r'"path"\s*"((?:\\.|[^"\\])*)"', re.IGNORECASE)
	old_entry = re.compile(r'^\s*"\d+"\s*"((?:\\.|[^"\\])*)"', re.MULTILINE)

	for root in roots:
		try:
			contents = (root / "steamapps" / "libraryfolders.vdf").read_text(
				encoding="utf-8-sig"
			)
		except OSError:
			continue

		# Current VDF format uses a "path" field; older versions stored paths directly under numeric library indexes.
		values = [match.group(1) for match in path_entry.finditer(contents)]
		values.extend(match.group(1) for match in old_entry.finditer(contents))
		for value in values:
			value = re.sub(r'\\([\\"])', r'\1', value)
			library = Path(value)
			if library.is_dir():
				libraries.add(library)

	return libraries


def normalize_name(name):
	return "".join(
		char
		for char in unicodedata.normalize("NFKD", name).casefold()
		if char.isalnum()
	)


def steam_app_type(app_id):
	# App manifests omit the app type, so use Steam Store metadata.
	url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&filters=basic"
	try:
		with urlopen(url, timeout=10) as response:
			payload = json.load(response)
	except (OSError, ValueError) as error:
		raise RuntimeError(
			f"Could not retrieve Steam Store details for app {app_id}: {error}"
		) from error

	app = payload.get(str(app_id)) if isinstance(payload, dict) else None
	if isinstance(app, dict) and app.get("success") is False:
		warnings.warn(
			f"Steam Store has no details for app {app_id}; excluding it because its type cannot be confirmed.",
			RuntimeWarning,
			stacklevel=2,
		)
		return None
	if not isinstance(app, dict) or app.get("success") is not True:
		raise RuntimeError(f"Steam Store did not return details for app {app_id}")

	data = app.get("data")
	if not isinstance(data, dict) or not isinstance(data.get("type"), str):
		raise TypeError(f"Steam Store details for app {app_id} have no app type")
	return data["type"]


def installed_games(search_query=None):
	# Return installed games as (name, app ID) pairs, sorted by name.
	games = {}
	appid_entry = re.compile(r'"appid"\s*"(\d+)"', re.IGNORECASE)
	name_entry = re.compile(r'"name"\s*"((?:\\.|[^"\\])*)"', re.IGNORECASE)
	normalized_query = normalize_name(search_query) if search_query else None

	for library in steam_libraries(steam_roots()):
		try:
			manifests = (library / "steamapps").glob("appmanifest_*.acf")
			for manifest in manifests:
				try:
					contents = manifest.read_text(encoding="utf-8-sig")
				except OSError:
					continue
				appid_match = appid_entry.search(contents)
				name_match = name_entry.search(contents)
				if appid_match and name_match:
					name = re.sub(r'\\([\\"])', r'\1', name_match.group(1))
					app_id = int(appid_match.group(1))
					if normalized_query and normalized_query not in normalize_name(name):
						continue
					if app_id not in games:
						app_type = steam_app_type(app_id)
						if app_type and app_type.casefold() == "game":
							games[app_id] = name
		except OSError:
			continue

	return sorted(
		((name, app_id) for app_id, name in games.items()),
		key=lambda game: (game[0].casefold(), game[0], game[1]),
	)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="List installed Steam games or search them by name."
	)
	parser.add_argument(
		"--search",
		metavar="NAME",
		help="show installed games whose names contain NAME",
	)
	args = parser.parse_args()
	if args.search is not None and not normalize_name(args.search):
		parser.error("search name must contain at least one letter or number")

	try:
		games = installed_games(args.search)
	except RuntimeError as error:
		parser.exit(1, f"Error: {error}\n")

	if args.search and not games:
		print(f"No installed games matched {args.search!r}.")
		raise SystemExit(0)

	name_width = max((len(name) for name, _ in games), default=0)
	id_width = max((len(str(app_id)) for _, app_id in games), default=2)
	name_width = max(name_width, len("Name"))
	print(f"{'Name':<{name_width}}  {'ID':>{id_width}}")
	for name, app_id in games:
		print(f"{name:<{name_width}}  {app_id:>{id_width}}")
