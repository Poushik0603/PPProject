# India News Desk

Simple Python desktop app that:

- fetches live news
- lets you search by keyword
- shows article details
- saves bookmarks locally
- works with offline demo data if the API is unavailable

## Why this version is simpler

- `gui.py` is much smaller and easier to read
- bookmarks use SQLite instead of MySQL
- no extra Python package is required
- setup is just Python + run

## Files

```text
main.py          starts the program
gui.py           simple Tkinter interface
api_handler.py   live news fetching and demo articles
database.py      local SQLite bookmark storage
bookmarks.db     created automatically when you run the app
```

## Run

```powershell
cd "C:\Users\royal\OneDrive\Documents\PP Projecr"
py main.py
```

## Optional API setup

If you want live news from GNews, set your API key first:

```powershell
$env:GNEWS_API_KEY="your_api_key"
$env:NEWS_COUNTRY="in"
```

If live fetching fails, the app automatically shows offline demo articles.
