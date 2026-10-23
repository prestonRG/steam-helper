import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from parse_steam_apps import installed_games, normalize_name


class SteamGamesApp:
	def __init__(self, root):
		self.root = root
		self.root.title("Steam Game Finder")
		self.root.geometry("620x480")
		self.root.minsize(420, 300)
		self.games = []
		self.results = queue.Queue()

		main = ttk.Frame(root, padding=16)
		main.grid(row=0, column=0, sticky="nsew")
		root.rowconfigure(0, weight=1)
		root.columnconfigure(0, weight=1)
		main.columnconfigure(0, weight=1)
		main.rowconfigure(3, weight=1)

		ttk.Label(main, text="Steam Game Finder", font=("Segoe UI", 16, "bold")).grid(
			row=0, column=0, columnspan=2, sticky="w"
		)
		ttk.Label(main, text="Search installed games by name").grid(
			row=1, column=0, columnspan=2, sticky="w", pady=(4, 12)
		)

		search_frame = ttk.Frame(main)
		search_frame.grid(row=2, column=0, columnspan=2, sticky="new")
		search_frame.columnconfigure(0, weight=1)
		self.search_var = tk.StringVar()
		self.search_var.trace_add("write", self._render_games)
		search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
		search_entry.grid(row=0, column=0, sticky="ew")
		search_entry.focus_set()
		self.refresh_button = ttk.Button(
			search_frame, text="Refresh", command=self.refresh
		)
		self.refresh_button.grid(row=0, column=1, padx=(8, 0))

		table_frame = ttk.Frame(main)
		table_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(12, 8))
		table_frame.columnconfigure(0, weight=1)
		table_frame.rowconfigure(0, weight=1)
		self.tree = ttk.Treeview(
			table_frame, columns=("name", "id"), show="headings", selectmode="browse"
		)
		self.tree.heading("name", text="Game name", anchor="w")
		self.tree.heading("id", text="App ID", anchor="e")
		self.tree.column("name", anchor="w", width=400)
		self.tree.column("id", anchor="e", width=100, stretch=False)
		scrollbar = ttk.Scrollbar(
			table_frame, orient="vertical", command=self.tree.yview
		)
		self.tree.configure(yscrollcommand=scrollbar.set)
		self.tree.grid(row=0, column=0, sticky="nsew")
		scrollbar.grid(row=0, column=1, sticky="ns")
		self.tree.bind("<Double-1>", self._copy_selected_id)

		footer = ttk.Frame(main)
		footer.grid(row=4, column=0, columnspan=2, sticky="ew")
		footer.columnconfigure(0, weight=1)
		self.status_var = tk.StringVar(value="Loading installed games...")
		ttk.Label(footer, textvariable=self.status_var).grid(
			row=0, column=0, sticky="w"
		)
		ttk.Button(footer, text="Copy ID", command=self._copy_selected_id).grid(
			row=0, column=1, padx=(8, 0)
		)

		self.root.after(100, self._check_results)
		self.refresh()

	def refresh(self):
		self.refresh_button.configure(state="disabled")
		self.status_var.set("Loading games and checking Steam Store details...")
		threading.Thread(target=self._load_games, daemon=True).start()

	def _load_games(self):
		try:
			games = installed_games()
		except RuntimeError as error:
			self.results.put(("error", str(error)))
		else:
			self.results.put(("success", games))

	def _check_results(self):
		try:
			result, value = self.results.get_nowait()
		except queue.Empty:
			self.root.after(100, self._check_results)
			return

		self.refresh_button.configure(state="normal")
		if result == "error":
			self.status_var.set("Could not load games.")
			messagebox.showerror("Steam Game Finder", value, parent=self.root)
			return

		self.games = value
		self.status_var.set("")
		self._render_games()

	def _render_games(self, *_):
		query = normalize_name(self.search_var.get())
		matches = [
			(name, app_id)
			for name, app_id in self.games
			if query in normalize_name(name)
		]
		self.tree.delete(*self.tree.get_children())
		for name, app_id in matches:
			self.tree.insert("", "end", values=(name, app_id))

		if self.games:
			self.status_var.set(f"Showing {len(matches)} of {len(self.games)} games")
		else:
			self.status_var.set("No installed games found.")

	def _copy_selected_id(self, _event=None):
		selected = self.tree.selection()
		if not selected:
			self.status_var.set("Select a game first.")
			return

		app_id = self.tree.item(selected[0], "values")[1]
		self.root.clipboard_clear()
		self.root.clipboard_append(app_id)
		self.status_var.set(f"Copied app ID {app_id}")


def main():
	root = tk.Tk()
	SteamGamesApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()
