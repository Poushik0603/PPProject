"""
gui.py – Tkinter GUI for News Fetcher + Bookmark System
Part C Requirement: Tkinter GUI with Entry, Listbox, Scrollbar, Menu, Dialogs.

Unique Features implemented here:
  1. Category filtering (dynamic API query)
  2. Keyword search
  3. Offline mode (view saved news without internet)
  4. Mark articles as 'Important' or 'Read Later'
  5. Auto-refresh news (interval-based)
  6. Highlight selected articles (colour coding by sentiment)
  7. Simple sentiment tagging (via api_handler.analyse_sentiment)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import webbrowser
import logging
from datetime import datetime

import api_handler
import database

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
COLORS = {
    "bg":           "#0b1220",
    "surface":      "#111a2b",
    "surface_alt":  "#172238",
    "accent":       "#f97316",
    "accent2":      "#16a34a",
    "accent3":      "#38bdf8",
    "text":         "#e5eefc",
    "text_dim":     "#94a3b8",
    "danger":       "#ef4444",
    "warning":      "#f59e0b",
    "success":      "#22c55e",
    "positive_bg":  "#10281f",
    "negative_bg":  "#2a1616",
    "neutral_bg":   "#12263b",
    "important_fg": "#fbbf24",
    "readlater_fg": "#38bdf8",
    "listbox_sel":  "#f97316",
    "border":       "#243146",
}

APP_TITLE = "India News Desk"
APP_SUBTITLE = "Live Indian headlines, bookmarks, and offline access in one polished desktop app."
DEFAULT_CATEGORY = "Nation"
DEFAULT_FEED_REGION = "India"
CATEGORY_OPTIONS = ["Nation"] + [
    name for name in api_handler.GNEWS_TOPICS.keys() if name != "Nation"
]

AUTO_REFRESH_MS = 300_000   # 5 minutes in milliseconds


# ─────────────────────────────────────────────
# MAIN APPLICATION WINDOW
# ─────────────────────────────────────────────

class NewsFetcherApp(tk.Tk):
    """
    Root Tk window – orchestrates all panes, threading, and state.
    """

    def __init__(self):
        super().__init__()

        # ── Window setup ──────────────────────────────────────────────
        self.title(APP_TITLE)
        self.geometry("1360x820")
        self.minsize(1100, 700)
        self.configure(bg=COLORS["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        # ── State variables ───────────────────────────────────────────
        self.articles:       list[dict] = []   # currently displayed live articles
        self.bookmarks:      list[dict] = []   # currently displayed bookmarks
        self.offline_mode    = tk.BooleanVar(value=False)
        self.auto_refresh_on = tk.BooleanVar(value=False)
        self.feed_country    = tk.StringVar(value=DEFAULT_FEED_REGION)
        self.feed_category   = tk.StringVar(value=DEFAULT_CATEGORY)
        self.article_count   = tk.StringVar(value="0")
        self.bookmark_count  = tk.StringVar(value="0")
        self.feed_summary    = tk.StringVar(
            value=f"{DEFAULT_FEED_REGION} feed • {DEFAULT_CATEGORY}"
        )
        self._auto_refresh_id: str | None = None  # after() callback id

        # ── Build UI ──────────────────────────────────────────────────
        self._build_hero()
        self._build_metrics_row()
        self._build_menu()
        self._build_header()
        self._build_status_bar()
        self._build_main_area()

        # ── Init DB & load initial news ────────────────────────────────
        database.initialize_database()
        self._load_news()

    # ─────────────────────────────────────────────
    # MENU BAR  (Part C requirement)
    # ─────────────────────────────────────────────

    def _build_hero(self) -> None:
        hero = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=14)
        hero.pack(fill=tk.X, padx=0, pady=(0, 2))

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
            fg=COLORS["text_dim"],
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        right = tk.Frame(hero, bg=COLORS["bg"])
        right.pack(side=tk.RIGHT, anchor="ne")

        badge = tk.Frame(right, bg=COLORS["surface_alt"], padx=12, pady=8)
        badge.pack(anchor="e")

        tk.Label(
            badge,
            textvariable=self.feed_summary,
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["surface_alt"],
            fg=COLORS["warning"],
        ).pack(anchor="e")
        tk.Label(
            badge,
            text="Updated from live APIs with an offline fallback",
            font=("Segoe UI", 9),
            bg=COLORS["surface_alt"],
            fg=COLORS["text_dim"],
        ).pack(anchor="e", pady=(2, 0))

    def _build_metrics_row(self) -> None:
        row = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=0)
        row.pack(fill=tk.X, padx=0, pady=(0, 10))

        metrics = [
            ("Live Articles", self.article_count, COLORS["accent"]),
            ("Saved Bookmarks", self.bookmark_count, COLORS["accent2"]),
            ("Current Feed", self.feed_summary, COLORS["accent3"]),
        ]

        for label, var, accent in metrics:
            card = tk.Frame(
                row,
                bg=COLORS["surface"],
                highlightthickness=1,
                highlightbackground=COLORS["border"],
            )
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
            tk.Frame(card, bg=accent, height=3).pack(fill=tk.X)
            tk.Label(
                card,
                text=label,
                font=("Segoe UI", 9),
                bg=COLORS["surface"],
                fg=COLORS["text_dim"],
            ).pack(anchor="w", padx=12, pady=(10, 0))
            tk.Label(
                card,
                textvariable=var,
                font=("Segoe UI", 14, "bold"),
                bg=COLORS["surface"],
                fg=COLORS["text"],
                wraplength=320,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(2, 10))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, bg=COLORS["surface"],
                          fg=COLORS["text"],
                          activebackground=COLORS["accent"],
                          activeforeground="#ffffff",
                          relief="flat", borderwidth=0)

        # ── File menu ─────────────────────────────────────────────────
        file_menu = tk.Menu(menubar, tearoff=False,
                            bg=COLORS["surface"], fg=COLORS["text"],
                            activebackground=COLORS["accent"],
                            activeforeground="#ffffff")
        file_menu.add_command(label="Open Bookmarks",
                              command=self._show_bookmarks_tab)
        file_menu.add_command(label="Export Bookmarks (CSV)",
                              command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",
                              command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        # ── View menu ─────────────────────────────────────────────────
        view_menu = tk.Menu(menubar, tearoff=False,
                            bg=COLORS["surface"], fg=COLORS["text"],
                            activebackground=COLORS["accent"],
                            activeforeground="#ffffff")
        view_menu.add_checkbutton(label="Offline Mode",
                                  variable=self.offline_mode,
                                  command=self._toggle_offline)
        view_menu.add_checkbutton(label="Auto-Refresh (5 min)",
                                  variable=self.auto_refresh_on,
                                  command=self._toggle_auto_refresh)
        menubar.add_cascade(label="View", menu=view_menu)

        # ── Help menu ─────────────────────────────────────────────────
        help_menu = tk.Menu(menubar, tearoff=False,
                            bg=COLORS["surface"], fg=COLORS["text"],
                            activebackground=COLORS["accent"],
                            activeforeground="#ffffff")
        help_menu.add_command(label="About",
                              command=self._show_about)
        help_menu.add_command(label="API Key Setup",
                              command=self._show_api_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ─────────────────────────────────────────────
    # HEADER  (search + filter controls)
    # ─────────────────────────────────────────────

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["surface"], pady=8)
        header.pack(fill=tk.X, padx=0, pady=0)

        # Title label
        tk.Label(header, text=APP_TITLE,
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["surface"],
                 fg=COLORS["accent"]).pack(side=tk.LEFT, padx=14)

        # ── Right-side controls ────────────────────────────────────────
        controls = tk.Frame(header, bg=COLORS["surface"])
        controls.pack(side=tk.RIGHT, padx=12)

        # Category dropdown
        tk.Label(controls, text="Category:",
                 bg=COLORS["surface"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 4))

        self.category_var = tk.StringVar(value=DEFAULT_CATEGORY)
        categories = CATEGORY_OPTIONS
        cat_menu = ttk.Combobox(controls, textvariable=self.category_var,
                                values=categories, width=14, state="readonly",
                                font=("Segoe UI", 10))
        cat_menu.pack(side=tk.LEFT, padx=(0, 8))
        cat_menu.bind("<<ComboboxSelected>>", lambda _: self._load_news())

        # Search Entry (Part C requirement)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(controls, textvariable=self.search_var,
                                width=28, font=("Segoe UI", 10),
                                bg=COLORS["bg"], fg=COLORS["text"],
                                insertbackground=COLORS["text"],
                                relief="flat", bd=4)
        search_entry.pack(side=tk.LEFT, padx=(0, 6))
        search_entry.bind("<Return>", lambda _: self._search_news())

        # Fetch / Search button (Part C requirement)
        self._styled_btn(controls, "Search",
                         self._search_news, COLORS["accent"]).pack(side=tk.LEFT, padx=2)
        self._styled_btn(controls, "Refresh",
                         self._load_news, COLORS["accent2"]).pack(side=tk.LEFT, padx=2)

    # ─────────────────────────────────────────────
    # MAIN AREA  (notebook tabs)
    # ─────────────────────────────────────────────

    def _build_main_area(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=COLORS["bg"],
                        borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=COLORS["surface"],
                        foreground=COLORS["text_dim"],
                        padding=[12, 6],
                        font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["accent"])],
                  foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        # Tab 1 – Live News
        self.tab_news = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.tab_news, text="Top India News")
        self._build_news_tab(self.tab_news)

        # Tab 2 – Saved Bookmarks
        self.tab_bookmarks = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.tab_bookmarks, text="Saved Bookmarks")
        self._build_bookmarks_tab(self.tab_bookmarks)

    # ── Tab 1: Live News ──────────────────────────────────────────────

    def _build_news_tab(self, parent: tk.Frame) -> None:
        # ── Left pane: Listbox + Scrollbar (Part C requirement) ────────
        left = tk.Frame(parent, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=8)

        list_frame = tk.Frame(left, bg=COLORS["border"], bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                 bg=COLORS["surface"])

        self.news_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 10),
            bg=COLORS["surface"],
            fg=COLORS["text"],
            selectbackground=COLORS["listbox_sel"],
            selectforeground="#ffffff",
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        scrollbar.config(command=self.news_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.news_listbox.pack(fill=tk.BOTH, expand=True)
        self.news_listbox.bind("<<ListboxSelect>>", self._on_article_select)
        self.news_listbox.bind("<Double-Button-1>", self._open_article_browser)

        # ── Right pane: article detail ────────────────────────────────
        right = tk.Frame(parent, bg=COLORS["surface"], width=340)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=8)
        right.pack_propagate(False)

        tk.Label(right, text="Article Detail",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["surface"], fg=COLORS["accent"]).pack(pady=(14, 6), padx=10)

        self.detail_title = tk.Label(
            right, text="Select an article →",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"],
            wraplength=300, justify=tk.LEFT, anchor="nw")
        self.detail_title.pack(fill=tk.X, padx=12, pady=(0, 6))

        self.detail_sentiment = tk.Label(
            right, text="", font=("Segoe UI", 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"])
        self.detail_sentiment.pack(padx=12, anchor="w")

        self.detail_source = tk.Label(
            right, text="", font=("Segoe UI", 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"])
        self.detail_source.pack(padx=12, anchor="w", pady=(2, 8))

        self.detail_desc = tk.Text(
            right, font=("Segoe UI", 9),
            bg=COLORS["bg"], fg=COLORS["text"],
            wrap=tk.WORD, relief="flat",
            height=10, state=tk.DISABLED,
            borderwidth=0, highlightthickness=0)
        self.detail_desc.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        # Action buttons
        btn_area = tk.Frame(right, bg=COLORS["surface"])
        btn_area.pack(fill=tk.X, padx=12, pady=6)

        self._styled_btn(btn_area, "Bookmark",
                         self._save_bookmark, COLORS["accent"]).pack(fill=tk.X, pady=2)
        self._styled_btn(btn_area, "Mark Important",
                         lambda: self._quick_tag("Important"),
                         COLORS["warning"]).pack(fill=tk.X, pady=2)
        self._styled_btn(btn_area, "Read Later",
                         lambda: self._quick_tag("Read Later"),
                         COLORS["accent2"]).pack(fill=tk.X, pady=2)
        self._styled_btn(btn_area, "Open in Browser",
                         self._open_article_browser,
                         COLORS["text_dim"]).pack(fill=tk.X, pady=2)
        self._styled_btn(btn_area, "Send Feedback (POST)",
                         self._send_feedback,
                         COLORS["text_dim"]).pack(fill=tk.X, pady=2)

    # ── Tab 2: Bookmarks ─────────────────────────────────────────────

    def _build_bookmarks_tab(self, parent: tk.Frame) -> None:
        # Toolbar
        toolbar = tk.Frame(parent, bg=COLORS["surface"], pady=6)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))

        tk.Label(toolbar, text="Filter:",
                 bg=COLORS["surface"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 4))

        self.bm_filter_var = tk.StringVar(value="All")
        self.bm_filter_combo = ttk.Combobox(
            toolbar, textvariable=self.bm_filter_var,
            values=["All"] + CATEGORY_OPTIONS,
            width=12, state="readonly", font=("Segoe UI", 9))
        self.bm_filter_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.bm_filter_combo.bind("<<ComboboxSelected>>",
                                  lambda _: self._refresh_bookmarks())

        tk.Label(toolbar, text="Search:",
                 bg=COLORS["surface"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.bm_search_var = tk.StringVar()
        bm_search = tk.Entry(toolbar, textvariable=self.bm_search_var,
                             width=20, font=("Segoe UI", 9),
                             bg=COLORS["bg"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], relief="flat", bd=3)
        bm_search.pack(side=tk.LEFT, padx=(0, 6))
        bm_search.bind("<Return>", lambda _: self._refresh_bookmarks())

        self._styled_btn(toolbar, "Search",
                         self._refresh_bookmarks, COLORS["accent"]).pack(side=tk.LEFT, padx=2)
        self._styled_btn(toolbar, "Show All",
                         lambda: [self.bm_search_var.set(""),
                                  self.bm_filter_var.set("All"),
                                  self._refresh_bookmarks()],
                         COLORS["text_dim"]).pack(side=tk.LEFT, padx=2)

        # Bookmark count label
        self.bm_count_label = tk.Label(toolbar, text="",
                                       bg=COLORS["surface"],
                                       fg=COLORS["text_dim"],
                                       font=("Segoe UI", 9))
        self.bm_count_label.pack(side=tk.RIGHT, padx=12)

        # ── Treeview ──────────────────────────────────────────────────
        tree_frame = tk.Frame(parent, bg=COLORS["border"], bd=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        style = ttk.Style()
        style.configure("Bookmarks.Treeview",
                        background=COLORS["surface"],
                        foreground=COLORS["text"],
                        fieldbackground=COLORS["surface"],
                        rowheight=28,
                        font=("Segoe UI", 9))
        style.configure("Bookmarks.Treeview.Heading",
                        background=COLORS["bg"],
                        foreground=COLORS["accent"],
                        font=("Segoe UI", 9, "bold"),
                        relief="flat")
        style.map("Bookmarks.Treeview",
                  background=[("selected", COLORS["listbox_sel"])],
                  foreground=[("selected", "#ffffff")])

        columns = ("title", "category", "sentiment", "tag", "saved_at")
        self.bm_tree = ttk.Treeview(
            tree_frame, columns=columns,
            show="headings", style="Bookmarks.Treeview",
            selectmode="browse")

        col_cfg = [
            ("title",     "Title",       380),
            ("category",  "Category",    100),
            ("sentiment", "Sentiment",    90),
            ("tag",       "Tag",          90),
            ("saved_at",  "Saved At",    140),
        ]
        for col_id, heading, width in col_cfg:
            self.bm_tree.heading(col_id, text=heading,
                                 command=lambda c=col_id: self._sort_tree(c))
            self.bm_tree.column(col_id, width=width, minwidth=60)

        bm_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                  command=self.bm_tree.yview)
        self.bm_tree.configure(yscrollcommand=bm_scroll.set)
        bm_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.bm_tree.pack(fill=tk.BOTH, expand=True)

        self.bm_tree.bind("<<TreeviewSelect>>", self._on_bookmark_select)
        self.bm_tree.bind("<Double-Button-1>", self._open_bookmark_browser)

        # ── Bookmark action buttons ────────────────────────────────────
        bm_actions = tk.Frame(parent, bg=COLORS["bg"], pady=6)
        bm_actions.pack(fill=tk.X, padx=8, pady=(0, 8))

        self._styled_btn(bm_actions, "Mark Important",
                         lambda: self._update_tag("Important"),
                         COLORS["warning"]).pack(side=tk.LEFT, padx=4)
        self._styled_btn(bm_actions, "Read Later",
                         lambda: self._update_tag("Read Later"),
                         COLORS["accent2"]).pack(side=tk.LEFT, padx=4)
        self._styled_btn(bm_actions, "Clear Tag",
                         lambda: self._update_tag("None"),
                         COLORS["text_dim"]).pack(side=tk.LEFT, padx=4)
        self._styled_btn(bm_actions, "Delete",
                         self._delete_bookmark,
                         COLORS["danger"]).pack(side=tk.LEFT, padx=4)
        self._styled_btn(bm_actions, "Open URL",
                         self._open_bookmark_browser,
                         COLORS["text_dim"]).pack(side=tk.LEFT, padx=4)

        self._refresh_bookmarks()

    # ─────────────────────────────────────────────
    # STATUS BAR
    # ─────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg=COLORS["surface"], height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.status_label = tk.Label(
            bar, text="Ready", font=("Segoe UI", 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"], anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.clock_label = tk.Label(
            bar, text="", font=("Segoe UI", 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"], anchor="e")
        self.clock_label.pack(side=tk.RIGHT, padx=10)
        self._update_clock()

    def _update_clock(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self._update_clock)

    def _set_status(self, msg: str) -> None:
        self.status_label.config(text=msg)
        logger.info("Status: %s", msg)

    def _sync_feed_summary(self) -> None:
        mode = "Offline" if self.offline_mode.get() else "Live"
        category = self.category_var.get() if hasattr(self, "category_var") else DEFAULT_CATEGORY
        self.feed_category.set(category)
        self.feed_summary.set(f"{DEFAULT_FEED_REGION} • {category} • {mode}")

    @staticmethod
    def _format_saved_at(value) -> str:
        """Normalise MySQL DATETIME values for the table display."""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M")
        if value is None:
            return ""
        return str(value)[:16]

    # ─────────────────────────────────────────────
    # NEWS LOADING  (threaded to keep GUI responsive)
    # ─────────────────────────────────────────────

    def _load_news(self) -> None:
        """Fetches top headlines in a background thread."""
        if self.offline_mode.get():
            self._load_offline_news()
            return

        self._set_status("⏳ Fetching news…")
        self._sync_feed_summary()
        self.news_listbox.delete(0, tk.END)
        self.news_listbox.insert(tk.END, "   Loading…")

        category = self.category_var.get()
        thread = threading.Thread(
            target=self._fetch_worker,
            args=(api_handler.fetch_top_headlines, category, "in"),
            daemon=True)
        thread.start()

    def _search_news(self) -> None:
        """Fetches search results in a background thread."""
        if self.offline_mode.get():
            self._load_offline_news()
            return

        query    = self.search_var.get().strip()
        category = self.category_var.get()
        self._set_status(f"⏳ Searching: '{query}' in {category}…")
        self._sync_feed_summary()
        self.news_listbox.delete(0, tk.END)
        self.news_listbox.insert(tk.END, "   Searching…")

        thread = threading.Thread(
            target=self._fetch_worker,
            args=(api_handler.search_news, query, category, "in"),
            daemon=True)
        thread.start()

    def _fetch_worker(self, fn, *args) -> None:
        """Worker runs in background thread; posts result to main thread."""
        try:
            articles = fn(*args)
            self.after(0, self._display_articles, articles, None)
        except ConnectionError as exc:
            self.after(0, self._display_articles, [], str(exc))
        except Exception as exc:
            self.after(0, self._display_articles, [], f"Unexpected error: {exc}")

    def _display_articles(self, articles: list[dict],
                          error: str | None) -> None:
        """Populates the Listbox with fetched articles (runs on main thread)."""
        self.news_listbox.delete(0, tk.END)
        self.articles = articles

        if error:
            self._set_status(f"⚠️ {error}")
            self.news_listbox.insert(tk.END,
                "  ⚠️  Could not load news. Check internet / API key.")
            self.news_listbox.insert(tk.END,
                "  🔌  Switching to Offline Mode…")
            self.offline_mode.set(True)
            self._sync_feed_summary()
            self._load_offline_news()
            return

        if not articles:
            self.news_listbox.insert(tk.END, "  No articles found.")
            self._set_status("No articles found.")
            self.article_count.set("0")
            self._sync_feed_summary()
            return

        # Populate listbox + apply sentiment background tags
        self.news_listbox.delete(0, tk.END)
        for i, art in enumerate(articles):
            sentiment = api_handler.analyse_sentiment(
                art["title"], art.get("description", ""))
            art["_sentiment"] = sentiment          # cache for detail pane

            # Colour per sentiment (Unique Feature: Highlight selected articles)
            tag = f"sent_{i}"
            if sentiment == "Positive":
                bg = COLORS["positive_bg"]
            elif sentiment == "Negative":
                bg = COLORS["negative_bg"]
            else:
                bg = COLORS["surface"]

            display_text = (
                f"  [{art.get('source','?')}]  {art['title']}"
            )
            self.news_listbox.insert(tk.END, display_text)
            self.news_listbox.itemconfig(i, background=bg, foreground=COLORS["text"])

        count = len(articles)
        cat   = self.category_var.get()
        self.article_count.set(str(count))
        self._sync_feed_summary()
        self._set_status(f"✅ {count} articles loaded  •  Category: {cat}")

    def _load_offline_news(self) -> None:
        """Displays saved bookmarks in the news pane (Offline Mode feature)."""
        cat  = self.category_var.get()
        arts = api_handler.get_demo_articles(cat)
        self.articles = arts
        self.article_count.set(str(len(arts)))
        self.news_listbox.delete(0, tk.END)
        for i, art in enumerate(arts):
            art["_sentiment"] = "Neutral"
            self.news_listbox.insert(tk.END, f"  [OFFLINE] {art['title']}")
            self.news_listbox.itemconfig(i,
                                         background=COLORS["neutral_bg"],
                                         foreground=COLORS["warning"])
        self._sync_feed_summary()
        self._set_status("🔌 Offline mode – showing demo data")

    # ─────────────────────────────────────────────
    # ARTICLE SELECTION / DETAIL PANE
    # ─────────────────────────────────────────────

    def _on_article_select(self, _event=None) -> None:
        sel = self.news_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.articles):
            return

        art       = self.articles[idx]
        sentiment = art.get("_sentiment", "Neutral")

        # Sentiment colour
        colour_map = {
            "Positive": COLORS["success"],
            "Negative": COLORS["danger"],
            "Neutral":  COLORS["text_dim"],
        }
        sent_colour = colour_map.get(sentiment, COLORS["text_dim"])

        self.detail_title.config(text=art["title"])
        self.detail_sentiment.config(
            text=f"Sentiment: {sentiment}  •  Source: {art.get('source','')}",
            fg=sent_colour)
        self.detail_source.config(
            text=f"Published: {art.get('published_at','')[:10]}")

        self.detail_desc.config(state=tk.NORMAL)
        self.detail_desc.delete("1.0", tk.END)
        self.detail_desc.insert(tk.END, art.get("description", ""))
        self.detail_desc.config(state=tk.DISABLED)

    # ─────────────────────────────────────────────
    # BOOKMARK OPERATIONS
    # ─────────────────────────────────────────────

    def _get_selected_article(self) -> dict | None:
        """Returns the currently selected article dict or None."""
        sel = self.news_listbox.curselection()
        if not sel or sel[0] >= len(self.articles):
            messagebox.showwarning("No Selection",
                                   "Please select an article first.")
            return None
        return self.articles[sel[0]]

    def _save_bookmark(self) -> None:
        art = self._get_selected_article()
        if not art:
            return

        sentiment = api_handler.analyse_sentiment(
            art["title"], art.get("description", ""))

        success = database.insert_bookmark(
            title       = art["title"],
            description = art.get("description", ""),
            url         = art.get("url", ""),
            category    = self.category_var.get(),
            sentiment   = sentiment,
            tag         = "None",
        )

        if success:
            messagebox.showinfo("Bookmarked ✅",
                                f"Article saved!\nSentiment: {sentiment}")
            self._refresh_bookmarks()
        else:
            messagebox.showwarning("Duplicate",
                                   "This article is already bookmarked.")

    def _quick_tag(self, tag: str) -> None:
        """Saves and immediately tags an article from the news tab."""
        art = self._get_selected_article()
        if not art:
            return

        sentiment = api_handler.analyse_sentiment(
            art["title"], art.get("description", ""))

        database.insert_bookmark(
            title       = art["title"],
            description = art.get("description", ""),
            url         = art.get("url", ""),
            category    = self.category_var.get(),
            sentiment   = sentiment,
            tag         = tag,
        )
        self._refresh_bookmarks()
        self._set_status(f"✅ Article saved with tag: {tag}")

    # ─────────────────────────────────────────────
    # BOOKMARKS TAB OPERATIONS
    # ─────────────────────────────────────────────

    def _refresh_bookmarks(self) -> None:
        """Reloads the bookmarks Treeview from the database."""
        for row in self.bm_tree.get_children():
            self.bm_tree.delete(row)

        keyword  = self.bm_search_var.get().strip()
        cat_filt = self.bm_filter_var.get()

        if keyword:
            bms = database.search_bookmarks(keyword)
        elif cat_filt and cat_filt != "All":
            bms = database.fetch_bookmarks_by_category(cat_filt)
        else:
            bms = database.fetch_all_bookmarks()

        self.bookmarks = bms

        for bm in bms:
            tag_val = bm.get("tag", "None")
            # Row tags for colour coding
            row_tag = "important" if tag_val == "Important" \
                      else "readlater" if tag_val == "Read Later" \
                      else ""

            self.bm_tree.insert(
                "", tk.END,
                iid=str(bm["id"]),
                values=(
                    bm["title"][:80] + ("…" if len(bm["title"]) > 80 else ""),
                    bm.get("category", ""),
                    bm.get("sentiment", ""),
                    tag_val,
                    self._format_saved_at(bm.get("saved_at")),
                ),
                tags=(row_tag,)
            )

        # Colour-code row tags
        self.bm_tree.tag_configure("important",
                                   foreground=COLORS["important_fg"])
        self.bm_tree.tag_configure("readlater",
                                   foreground=COLORS["readlater_fg"])

        count = len(bms)
        self.bookmark_count.set(str(count))
        self.bm_count_label.config(text=f"{count} bookmark{'s' if count != 1 else ''}")
        self._set_status(f"Bookmarks refreshed — {count} shown")

    def _get_selected_bookmark(self) -> dict | None:
        sel = self.bm_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select a bookmark first.")
            return None
        bm_id = int(sel[0])
        return database.fetch_bookmark_by_id(bm_id)

    def _on_bookmark_select(self, _event=None) -> None:
        """Shows selected bookmark URL in status bar."""
        bm = self._get_selected_bookmark()
        if bm:
            self._set_status(f"URL: {bm.get('url','')}")

    def _update_tag(self, tag: str) -> None:
        bm = self._get_selected_bookmark()
        if not bm:
            return
        database.update_bookmark_tag(bm["id"], tag)
        self._refresh_bookmarks()
        self._set_status(f"Tag updated → {tag}")

    def _delete_bookmark(self) -> None:
        bm = self._get_selected_bookmark()
        if not bm:
            return
        if messagebox.askyesno("Delete Bookmark",
                               f"Delete bookmark:\n\n{bm['title']}\n\nThis cannot be undone."):
            database.delete_bookmark(bm["id"])
            self._refresh_bookmarks()
            self._set_status("🗑️ Bookmark deleted.")

    def _open_bookmark_browser(self, _event=None) -> None:
        bm = self._get_selected_bookmark()
        if bm and bm.get("url"):
            webbrowser.open(bm["url"])

    def _sort_tree(self, col: str) -> None:
        """Sort the Treeview by a column."""
        data = [(self.bm_tree.set(child, col), child)
                for child in self.bm_tree.get_children("")]
        data.sort()
        for idx, (_, child) in enumerate(data):
            self.bm_tree.move(child, "", idx)

    # ─────────────────────────────────────────────
    # BROWSER / FEEDBACK / EXPORT
    # ─────────────────────────────────────────────

    def _open_article_browser(self, _event=None) -> None:
        art = self._get_selected_article()
        if art and art.get("url"):
            webbrowser.open(art["url"])

    def _send_feedback(self) -> None:
        """Demonstrates HTTP POST via api_handler.post_feedback."""
        art = self._get_selected_article()
        if not art:
            return

        rating = simpledialog.askinteger(
            "Rate Article", "Rate this article (1 = Poor, 5 = Excellent):",
            minvalue=1, maxvalue=5, parent=self)
        if rating is None:
            return

        self._set_status("📤 Sending POST feedback…")

        def worker():
            result = api_handler.post_feedback(art["url"], rating)
            msg = "✅ Feedback sent via POST!" if result["success"] \
                  else f"⚠️ POST failed: {result.get('error','')}"
            self.after(0, self._set_status, msg)
            self.after(0, messagebox.showinfo, "POST Result", msg)

        threading.Thread(target=worker, daemon=True).start()

    def _export_csv(self) -> None:
        """Exports all bookmarks to a CSV file."""
        import csv, os
        bms  = database.fetch_all_bookmarks()
        path = os.path.join(os.path.expanduser("~"), "news_bookmarks_export.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["id","title","description","url",
                                   "category","sentiment","tag","saved_at"])
                writer.writeheader()
                writer.writerows(bms)
            messagebox.showinfo("Export Complete",
                                f"Bookmarks exported to:\n{path}")
            self._set_status(f"📁 Exported {len(bms)} bookmarks.")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    # ─────────────────────────────────────────────
    # AUTO-REFRESH  (Unique Feature)
    # ─────────────────────────────────────────────

    def _toggle_auto_refresh(self) -> None:
        if self.auto_refresh_on.get():
            self._schedule_auto_refresh()
            self._set_status("🔄 Auto-refresh ON (every 5 minutes)")
        else:
            if self._auto_refresh_id:
                self.after_cancel(self._auto_refresh_id)
                self._auto_refresh_id = None
            self._set_status("🔄 Auto-refresh OFF")

    def _schedule_auto_refresh(self) -> None:
        if self.auto_refresh_on.get():
            self._load_news()
            self._auto_refresh_id = self.after(
                AUTO_REFRESH_MS, self._schedule_auto_refresh)

    # ─────────────────────────────────────────────
    # OFFLINE MODE TOGGLE
    # ─────────────────────────────────────────────

    def _toggle_offline(self) -> None:
        if self.offline_mode.get():
            self._sync_feed_summary()
            self._load_offline_news()
        else:
            self._load_news()

    # ─────────────────────────────────────────────
    # DIALOGS
    # ─────────────────────────────────────────────

    def _on_exit(self) -> None:
        """Exit with confirmation dialog (Part C requirement)."""
        if messagebox.askyesno("Exit",
                               f"Are you sure you want to exit {APP_TITLE}?"):
            if self._auto_refresh_id:
                self.after_cancel(self._auto_refresh_id)
            self.destroy()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About India News Desk",
            f"{APP_TITLE}\n"
            "Version 1.0\n\n"
            "Part B: urllib HTTP GET & POST\n"
            "Part C: Tkinter GUI + MySQL CRUD\n\n"
            "Academic Project – Python Desktop Application\n"
            "Built with: Python | Tkinter | MySQL | urllib"
        )

    def _show_api_help(self) -> None:
        messagebox.showinfo(
            "API Key Setup",
            "To use live news:\n\n"
            "1. Visit https://gnews.io (free tier available)\n"
            "2. Register and copy your API key\n"
            "3. Set GNEWS_API_KEY in your environment\n"
            "4. Keep NEWS_PROVIDER='gnews' and NEWS_COUNTRY='in'\n"
            "5. Restart the application\n\n"
            "Alternatively use https://newsapi.org and set\n"
            "NEWS_PROVIDER='newsapi' in your environment"
        )

    def _show_bookmarks_tab(self) -> None:
        self.notebook.select(self.tab_bookmarks)

    # ─────────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────────

    @staticmethod
    def _styled_btn(parent, text: str, command,
                    bg: str) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 9),
            bg=bg, fg="#ffffff",
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            relief="flat", bd=0, padx=10, pady=5,
            cursor="hand2",
        )
