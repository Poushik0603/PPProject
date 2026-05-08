"""
gui.py - Styled but compact Tkinter GUI for the news project.

This keeps the polished feel of the original interface while reducing the
amount of code to the essentials:
- fetch or search news
- read article details
- save bookmarks
- manage saved bookmarks
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import api_handler
import database


COLORS = {
    "bg": "#0b1220",
    "panel": "#111a2b",
    "panel_alt": "#172238",
    "border": "#243146",
    "text": "#e5eefc",
    "muted": "#94a3b8",
    "accent": "#f97316",
    "accent2": "#16a34a",
    "warning": "#f59e0b",
    "positive": "#10281f",
    "negative": "#2a1616",
    "neutral": "#12263b",
}

APP_TITLE = "India News Desk"
APP_SUBTITLE = "Live headlines, saved bookmarks, and an offline fallback in one simple desktop app."
CATEGORIES = ["Nation"] + [name for name in api_handler.GNEWS_TOPICS if name != "Nation"]


class NewsFetcherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1220x760")
        self.minsize(980, 640)
        self.configure(bg=COLORS["bg"])

        self.articles: list[dict] = []
        self.bookmarks: list[dict] = []

        self.category_var = tk.StringVar(value="Nation")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.feed_var = tk.StringVar(value="India • Nation")
        self.article_count_var = tk.StringVar(value="0")
        self.bookmark_count_var = tk.StringVar(value="0")
        self.bookmark_search_var = tk.StringVar()

        self._configure_styles()
        self._build_layout()
        self.refresh_bookmarks()
        self.load_news()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            padding=(14, 8),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Bookmarks.Treeview",
            background=COLORS["panel"],
            fieldbackground=COLORS["panel"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            rowheight=28,
        )
        style.configure(
            "Bookmarks.Treeview.Heading",
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            relief="flat",
        )
        style.map("Bookmarks.Treeview", background=[("selected", COLORS["accent"])])

    def _build_layout(self) -> None:
        self._build_hero()
        self._build_header()
        self._build_tabs()
        self._build_status_bar()

    def _build_hero(self) -> None:
        hero = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=14)
        hero.pack(fill=tk.X)

        left = tk.Frame(hero, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            left,
            text=APP_TITLE,
            font=("Segoe UI", 22, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"],
        ).pack(anchor="w")
        tk.Label(
            left,
            text=APP_SUBTITLE,
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

        stats = tk.Frame(hero, bg=COLORS["bg"])
        stats.pack(side=tk.RIGHT)
        self._stat_card(stats, "Articles", self.article_count_var, COLORS["accent"]).pack(side=tk.LEFT, padx=6)
        self._stat_card(stats, "Bookmarks", self.bookmark_count_var, COLORS["accent2"]).pack(side=tk.LEFT, padx=6)
        self._stat_card(stats, "Feed", self.feed_var, COLORS["warning"]).pack(side=tk.LEFT, padx=6)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["panel"], padx=14, pady=10)
        header.pack(fill=tk.X, padx=8)

        tk.Label(
            header,
            text="Category",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT)

        category_box = ttk.Combobox(
            header,
            textvariable=self.category_var,
            values=CATEGORIES,
            state="readonly",
            width=16,
        )
        category_box.pack(side=tk.LEFT, padx=(8, 12))
        category_box.bind("<<ComboboxSelected>>", lambda _event: self.load_news())

        search = tk.Entry(
            header,
            textvariable=self.search_var,
            width=34,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            bd=6,
        )
        search.pack(side=tk.LEFT, padx=(0, 8))
        search.bind("<Return>", lambda _event: self.search_news())

        self._button(header, "Search", self.search_news, COLORS["accent"]).pack(side=tk.LEFT, padx=2)
        self._button(header, "Refresh", self.load_news, COLORS["accent2"]).pack(side=tk.LEFT, padx=2)
        self._button(header, "Offline", self.load_offline_news, COLORS["warning"]).pack(side=tk.LEFT, padx=2)

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        news_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        bookmarks_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(news_tab, text="Top News")
        self.notebook.add(bookmarks_tab, text="Bookmarks")

        self._build_news_tab(news_tab)
        self._build_bookmarks_tab(bookmarks_tab)

    def _build_news_tab(self, parent: tk.Widget) -> None:
        left = tk.Frame(parent, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        list_frame = tk.Frame(left, bg=COLORS["border"], padx=1, pady=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.news_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            activestyle="none",
        )
        self.news_listbox.pack(fill=tk.BOTH, expand=True)
        self.news_listbox.bind("<<ListboxSelect>>", self.on_article_select)
        self.news_listbox.bind("<Double-Button-1>", self.open_article)
        scrollbar.config(command=self.news_listbox.yview)

        right = tk.Frame(parent, bg=COLORS["panel"], width=360)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=8)
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Article Details",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["accent"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.detail_title = tk.Label(
            right,
            text="Select an article",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["text"],
            wraplength=320,
            justify="left",
        )
        self.detail_title.pack(fill=tk.X, padx=14)

        self.detail_meta = tk.Label(
            right,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            wraplength=320,
            justify="left",
        )
        self.detail_meta.pack(fill=tk.X, padx=14, pady=(6, 8))

        self.detail_desc = tk.Text(
            right,
            height=14,
            wrap="word",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.detail_desc.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
        self.detail_desc.config(state=tk.DISABLED)

        actions = tk.Frame(right, bg=COLORS["panel"])
        actions.pack(fill=tk.X, padx=14, pady=(0, 14))
        self._button(actions, "Save Bookmark", self.save_bookmark, COLORS["accent"]).pack(fill=tk.X, pady=2)
        self._button(actions, "Mark Important", lambda: self.quick_tag("Important"), COLORS["warning"]).pack(fill=tk.X, pady=2)
        self._button(actions, "Read Later", lambda: self.quick_tag("Read Later"), COLORS["accent2"]).pack(fill=tk.X, pady=2)
        self._button(actions, "Open in Browser", self.open_article, COLORS["panel_alt"]).pack(fill=tk.X, pady=2)

    def _build_bookmarks_tab(self, parent: tk.Widget) -> None:
        toolbar = tk.Frame(parent, bg=COLORS["panel"], padx=12, pady=10)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))

        search = tk.Entry(
            toolbar,
            textvariable=self.bookmark_search_var,
            width=28,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            bd=6,
        )
        search.pack(side=tk.LEFT, padx=(0, 8))
        search.bind("<Return>", lambda _event: self.refresh_bookmarks())

        self._button(toolbar, "Search Saved", self.refresh_bookmarks, COLORS["accent"]).pack(side=tk.LEFT, padx=2)
        self._button(toolbar, "Show All", self.show_all_bookmarks, COLORS["panel_alt"]).pack(side=tk.LEFT, padx=2)

        table_wrap = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        columns = ("title", "category", "tag", "saved")
        self.bookmark_tree = ttk.Treeview(
            table_wrap,
            columns=columns,
            show="headings",
            style="Bookmarks.Treeview",
        )
        for name, label, width in (
            ("title", "Title", 420),
            ("category", "Category", 120),
            ("tag", "Tag", 120),
            ("saved", "Saved", 150),
        ):
            self.bookmark_tree.heading(name, text=label)
            self.bookmark_tree.column(name, width=width, anchor="w")
        self.bookmark_tree.pack(fill=tk.BOTH, expand=True)
        self.bookmark_tree.bind("<Double-1>", self.open_bookmark)

        actions = tk.Frame(parent, bg=COLORS["bg"])
        actions.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._button(actions, "Open Bookmark", self.open_bookmark, COLORS["accent2"]).pack(side=tk.LEFT, padx=2)
        self._button(actions, "Delete", self.delete_bookmark, COLORS["warning"]).pack(side=tk.LEFT, padx=2)
        self._button(actions, "Important", lambda: self.update_bookmark_tag("Important"), COLORS["accent"]).pack(side=tk.LEFT, padx=2)
        self._button(actions, "Read Later", lambda: self.update_bookmark_tag("Read Later"), COLORS["panel_alt"]).pack(side=tk.LEFT, padx=2)

    def _build_status_bar(self) -> None:
        bar = tk.Label(
            self,
            textvariable=self.status_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            anchor="w",
            padx=10,
            pady=6,
        )
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _stat_card(self, parent: tk.Widget, label: str, var: tk.StringVar, accent: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        tk.Frame(frame, bg=accent, height=3).pack(fill=tk.X)
        tk.Label(frame, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(frame, textvariable=var, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 13, "bold"), wraplength=220, justify="left").pack(anchor="w", padx=10, pady=(2, 8))
        return frame

    def _button(self, parent: tk.Widget, text: str, command, bg: str) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="#ffffff",
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
        )

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def sync_summary(self, mode: str = "Live") -> None:
        category = self.category_var.get()
        self.feed_var.set(f"India • {category} • {mode}")

    def run_fetch(self, worker_fn, success_message: str) -> None:
        self.set_status("Loading news...")
        self.sync_summary()
        self.news_listbox.delete(0, tk.END)
        self.news_listbox.insert(tk.END, "  Loading...")

        def task() -> None:
            try:
                articles = worker_fn()
                self.after(0, lambda: self.show_articles(articles, success_message, "Live"))
            except Exception:
                self.after(0, self.load_offline_news)

        threading.Thread(target=task, daemon=True).start()

    def load_news(self) -> None:
        category = self.category_var.get()
        self.run_fetch(
            lambda: api_handler.fetch_top_headlines(category=category),
            f"Loaded top news for {category}.",
        )

    def search_news(self) -> None:
        query = self.search_var.get().strip()
        category = self.category_var.get()
        if not query:
            self.load_news()
            return
        self.run_fetch(
            lambda: api_handler.search_news(query=query, category=category),
            f"Search complete for '{query}'.",
        )

    def load_offline_news(self) -> None:
        category = self.category_var.get()
        self.show_articles(
            api_handler.get_demo_articles(category),
            "Live fetch failed. Showing offline demo articles.",
            "Offline",
        )

    def show_articles(self, articles: list[dict], status: str, mode: str) -> None:
        self.articles = articles
        self.article_count_var.set(str(len(articles)))
        self.sync_summary(mode)

        self.news_listbox.delete(0, tk.END)
        for index, article in enumerate(articles):
            sentiment = api_handler.analyse_sentiment(article["title"], article.get("description", ""))
            article["_sentiment"] = sentiment
            self.news_listbox.insert(tk.END, f"  [{article.get('source', '?')}] {article['title']}")
            bg = COLORS["positive"] if sentiment == "Positive" else COLORS["negative"] if sentiment == "Negative" else COLORS["panel"]
            self.news_listbox.itemconfig(index, background=bg, foreground=COLORS["text"])

        if articles:
            self.news_listbox.selection_set(0)
            self.on_article_select()
        else:
            self.clear_details()

        self.set_status(status)

    def clear_details(self) -> None:
        self.detail_title.config(text="Select an article")
        self.detail_meta.config(text="")
        self.detail_desc.config(state=tk.NORMAL)
        self.detail_desc.delete("1.0", tk.END)
        self.detail_desc.config(state=tk.DISABLED)

    def get_selected_article(self, warn: bool = False) -> dict | None:
        selected = self.news_listbox.curselection()
        if not selected or selected[0] >= len(self.articles):
            if warn:
                messagebox.showwarning("No Selection", "Please select an article first.")
            return None
        return self.articles[selected[0]]

    def on_article_select(self, _event=None) -> None:
        article = self.get_selected_article()
        if not article:
            return

        published = article.get("published_at", "")[:10]
        sentiment = article.get("_sentiment", "Neutral")
        self.detail_title.config(text=article["title"])
        self.detail_meta.config(
            text=f"Source: {article.get('source', 'Unknown')}  |  Sentiment: {sentiment}  |  Published: {published}"
        )
        self.detail_desc.config(state=tk.NORMAL)
        self.detail_desc.delete("1.0", tk.END)
        self.detail_desc.insert(tk.END, article.get("description", "No description available."))
        self.detail_desc.config(state=tk.DISABLED)

    def save_bookmark(self) -> None:
        article = self.get_selected_article(warn=True)
        if not article:
            return

        saved = database.insert_bookmark(
            title=article["title"],
            description=article.get("description", ""),
            url=article.get("url", ""),
            category=self.category_var.get(),
            sentiment=article.get("_sentiment", "Neutral"),
            tag="None",
        )
        if saved:
            self.refresh_bookmarks()
            self.set_status("Bookmark saved.")
        else:
            messagebox.showinfo("Duplicate", "This article is already bookmarked.")

    def quick_tag(self, tag: str) -> None:
        article = self.get_selected_article(warn=True)
        if not article:
            return

        database.insert_bookmark(
            title=article["title"],
            description=article.get("description", ""),
            url=article.get("url", ""),
            category=self.category_var.get(),
            sentiment=article.get("_sentiment", "Neutral"),
            tag=tag,
        )
        self.refresh_bookmarks()
        self.set_status(f"Saved article as {tag}.")

    def open_article(self, _event=None) -> None:
        article = self.get_selected_article(warn=True)
        if article and article.get("url"):
            webbrowser.open(article["url"])

    def refresh_bookmarks(self) -> None:
        keyword = self.bookmark_search_var.get().strip()
        self.bookmarks = database.search_bookmarks(keyword) if keyword else database.fetch_all_bookmarks()

        for item in self.bookmark_tree.get_children():
            self.bookmark_tree.delete(item)

        for bookmark in self.bookmarks:
            self.bookmark_tree.insert(
                "",
                tk.END,
                iid=str(bookmark["id"]),
                values=(
                    bookmark["title"][:70] + ("..." if len(bookmark["title"]) > 70 else ""),
                    bookmark.get("category", ""),
                    bookmark.get("tag", "None"),
                    str(bookmark.get("saved_at", ""))[:16],
                ),
            )

        self.bookmark_count_var.set(str(len(self.bookmarks)))
        self.set_status(f"{len(self.bookmarks)} bookmark(s) shown.")

    def show_all_bookmarks(self) -> None:
        self.bookmark_search_var.set("")
        self.refresh_bookmarks()

    def get_selected_bookmark(self, warn: bool = False) -> dict | None:
        selected = self.bookmark_tree.selection()
        if not selected:
            if warn:
                messagebox.showwarning("No Selection", "Please select a bookmark first.")
            return None
        return database.fetch_bookmark_by_id(int(selected[0]))

    def open_bookmark(self, _event=None) -> None:
        bookmark = self.get_selected_bookmark(warn=True)
        if bookmark and bookmark.get("url"):
            webbrowser.open(bookmark["url"])

    def update_bookmark_tag(self, tag: str) -> None:
        bookmark = self.get_selected_bookmark(warn=True)
        if not bookmark:
            return
        database.update_bookmark_tag(bookmark["id"], tag)
        self.refresh_bookmarks()
        self.set_status(f"Bookmark marked as {tag}.")

    def delete_bookmark(self) -> None:
        bookmark = self.get_selected_bookmark(warn=True)
        if not bookmark:
            return
        if messagebox.askyesno("Delete Bookmark", f"Delete '{bookmark['title']}'?"):
            database.delete_bookmark(bookmark["id"])
            self.refresh_bookmarks()
            self.set_status("Bookmark deleted.")
