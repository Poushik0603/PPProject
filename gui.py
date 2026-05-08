"""
gui.py - A small Tkinter interface for the news fetcher project.

This version focuses on the core workflow:
1. fetch news
2. search news
3. view article details
4. save bookmarks
5. open or delete bookmarks
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import api_handler
import database


CATEGORIES = list(api_handler.GNEWS_TOPICS.keys())


class NewsFetcherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("India News Desk")
        self.geometry("1000x620")

        self.articles: list[dict] = []
        self.bookmarks: list[dict] = []

        self.category_var = tk.StringVar(value="Nation")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self._build_layout()
        self.refresh_bookmarks()
        self.load_news()

    def _build_layout(self) -> None:
        top = tk.Frame(self, padx=10, pady=10)
        top.pack(fill=tk.X)

        tk.Label(top, text="Category").pack(side=tk.LEFT)
        ttk.Combobox(
            top,
            textvariable=self.category_var,
            values=CATEGORIES,
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=(5, 10))

        tk.Entry(top, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(top, text="Fetch Top News", command=self.load_news).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Search", command=self.search_news).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Offline Demo", command=self.load_offline_news).pack(side=tk.LEFT, padx=3)

        body = tk.PanedWindow(self, sashrelief=tk.RAISED)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body)
        right = tk.Frame(body)
        body.add(left, minsize=360)
        body.add(right, minsize=360)

        self._build_articles_panel(left)
        self._build_bookmarks_panel(right)

        status = tk.Label(self, textvariable=self.status_var, anchor="w", bd=1, relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_articles_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text="Articles", padx=8, pady=8)
        frame.pack(fill=tk.BOTH, expand=True, padx=(0, 5))

        list_frame = tk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.news_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.news_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.news_listbox.bind("<<ListboxSelect>>", self.on_article_select)
        self.news_listbox.bind("<Double-Button-1>", self.open_article)
        scrollbar.config(command=self.news_listbox.yview)

        tk.Label(frame, text="Title").pack(anchor="w", pady=(8, 0))
        self.article_title = tk.Label(frame, text="", anchor="w", justify="left", wraplength=420, font=("Segoe UI", 11, "bold"))
        self.article_title.pack(fill=tk.X)

        self.article_meta = tk.Label(frame, text="", anchor="w", justify="left")
        self.article_meta.pack(fill=tk.X, pady=(4, 0))

        tk.Label(frame, text="Description").pack(anchor="w", pady=(8, 0))
        self.article_text = tk.Text(frame, height=10, wrap="word")
        self.article_text.pack(fill=tk.BOTH, expand=False)
        self.article_text.config(state=tk.DISABLED)

        buttons = tk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(8, 0))
        tk.Button(buttons, text="Save Bookmark", command=self.save_bookmark).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons, text="Open Article", command=self.open_article).pack(side=tk.LEFT)

    def _build_bookmarks_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text="Bookmarks", padx=8, pady=8)
        frame.pack(fill=tk.BOTH, expand=True, padx=(5, 0))

        top = tk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 8))

        self.bookmark_search_var = tk.StringVar()
        tk.Entry(top, textvariable=self.bookmark_search_var, width=25).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(top, text="Search Saved", command=self.refresh_bookmarks).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(top, text="Show All", command=self.show_all_bookmarks).pack(side=tk.LEFT)

        columns = ("title", "category", "tag")
        self.bookmark_tree = ttk.Treeview(frame, columns=columns, show="headings", height=16)
        self.bookmark_tree.heading("title", text="Title")
        self.bookmark_tree.heading("category", text="Category")
        self.bookmark_tree.heading("tag", text="Tag")
        self.bookmark_tree.column("title", width=260)
        self.bookmark_tree.column("category", width=90)
        self.bookmark_tree.column("tag", width=90)
        self.bookmark_tree.pack(fill=tk.BOTH, expand=True)
        self.bookmark_tree.bind("<Double-1>", self.open_bookmark)

        buttons = tk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(8, 0))
        tk.Button(buttons, text="Open Bookmark", command=self.open_bookmark).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons, text="Delete Bookmark", command=self.delete_bookmark).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons, text="Mark Important", command=lambda: self.update_bookmark_tag("Important")).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons, text="Mark Read Later", command=lambda: self.update_bookmark_tag("Read Later")).pack(side=tk.LEFT)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def run_in_background(self, task, success_message: str) -> None:
        self.set_status("Loading...")

        def worker() -> None:
            try:
                articles = task()
                self.after(0, lambda: self.show_articles(articles, success_message))
            except Exception as exc:
                self.after(0, lambda: self.load_offline_news(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def load_news(self) -> None:
        category = self.category_var.get()
        self.run_in_background(
            lambda: api_handler.fetch_top_headlines(category=category),
            f"Loaded top news for {category}",
        )

    def search_news(self) -> None:
        query = self.search_var.get().strip()
        category = self.category_var.get()
        if not query:
            self.load_news()
            return
        self.run_in_background(
            lambda: api_handler.search_news(query=query, category=category),
            f"Search complete for '{query}'",
        )

    def load_offline_news(self, error_message: str | None = None) -> None:
        category = self.category_var.get()
        message = "Showing offline demo articles."
        if error_message:
            message = f"Live fetch failed. {message}"
        self.show_articles(api_handler.get_demo_articles(category), message)

    def show_articles(self, articles: list[dict], status_message: str) -> None:
        self.articles = articles
        self.news_listbox.delete(0, tk.END)

        for article in articles:
            source = article.get("source", "Unknown")
            self.news_listbox.insert(tk.END, f"[{source}] {article['title']}")

        if articles:
            self.news_listbox.selection_set(0)
            self.on_article_select()
        else:
            self.clear_article_details()

        self.set_status(status_message)

    def clear_article_details(self) -> None:
        self.article_title.config(text="")
        self.article_meta.config(text="")
        self.article_text.config(state=tk.NORMAL)
        self.article_text.delete("1.0", tk.END)
        self.article_text.config(state=tk.DISABLED)

    def on_article_select(self, _event=None) -> None:
        article = self.get_selected_article()
        if not article:
            return

        sentiment = api_handler.analyse_sentiment(
            article["title"],
            article.get("description", ""),
        )
        published = article.get("published_at", "")[:19].replace("T", " ")

        self.article_title.config(text=article["title"])
        self.article_meta.config(
            text=f"Source: {article.get('source', 'Unknown')} | Sentiment: {sentiment} | Published: {published}"
        )
        self.article_text.config(state=tk.NORMAL)
        self.article_text.delete("1.0", tk.END)
        self.article_text.insert(tk.END, article.get("description", "No description available."))
        self.article_text.config(state=tk.DISABLED)

    def get_selected_article(self) -> dict | None:
        selection = self.news_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.articles):
            return None
        return self.articles[index]

    def save_bookmark(self) -> None:
        article = self.get_selected_article()
        if not article:
            messagebox.showwarning("No selection", "Please select an article first.")
            return

        sentiment = api_handler.analyse_sentiment(article["title"], article.get("description", ""))
        saved = database.insert_bookmark(
            title=article["title"],
            description=article.get("description", ""),
            url=article.get("url", ""),
            category=self.category_var.get(),
            sentiment=sentiment,
            tag="None",
        )
        if saved:
            self.refresh_bookmarks()
            self.set_status("Bookmark saved.")
        else:
            messagebox.showinfo("Already saved", "This article is already bookmarked.")

    def open_article(self, _event=None) -> None:
        article = self.get_selected_article()
        if article and article.get("url"):
            webbrowser.open(article["url"])

    def refresh_bookmarks(self) -> None:
        keyword = self.bookmark_search_var.get().strip()
        if keyword:
            self.bookmarks = database.search_bookmarks(keyword)
        else:
            self.bookmarks = database.fetch_all_bookmarks()

        for item in self.bookmark_tree.get_children():
            self.bookmark_tree.delete(item)

        for bookmark in self.bookmarks:
            self.bookmark_tree.insert(
                "",
                tk.END,
                iid=str(bookmark["id"]),
                values=(
                    bookmark["title"][:60],
                    bookmark.get("category", ""),
                    bookmark.get("tag", "None"),
                ),
            )

        self.set_status(f"{len(self.bookmarks)} bookmark(s) shown.")

    def show_all_bookmarks(self) -> None:
        self.bookmark_search_var.set("")
        self.refresh_bookmarks()

    def get_selected_bookmark(self) -> dict | None:
        selected = self.bookmark_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a bookmark first.")
            return None
        return database.fetch_bookmark_by_id(int(selected[0]))

    def open_bookmark(self, _event=None) -> None:
        bookmark = self.get_selected_bookmark()
        if bookmark and bookmark.get("url"):
            webbrowser.open(bookmark["url"])

    def update_bookmark_tag(self, tag: str) -> None:
        bookmark = self.get_selected_bookmark()
        if not bookmark:
            return
        database.update_bookmark_tag(bookmark["id"], tag)
        self.refresh_bookmarks()
        self.set_status(f"Bookmark marked as {tag}.")

    def delete_bookmark(self) -> None:
        bookmark = self.get_selected_bookmark()
        if not bookmark:
            return
        if messagebox.askyesno("Delete bookmark", f"Delete '{bookmark['title']}'?"):
            database.delete_bookmark(bookmark["id"])
            self.refresh_bookmarks()
            self.set_status("Bookmark deleted.")
