# India News Desk + Bookmark System

Python desktop application that fetches live India-focused news from GNews/NewsAPI, displays it in a polished Tkinter GUI, and stores bookmarks in a MySQL database.

## Project Structure

```text
main.py          Entry point
gui.py           Tkinter GUI and dashboard layout
api_handler.py   urllib HTTP GET/POST, JSON parsing, sentiment
database.py      MySQL CRUD and schema initialization
schema.sql       Optional standalone MySQL schema
requirements.txt Python package dependencies
```

## Requirements

| Item | Version |
| --- | --- |
| Python | 3.10+ |
| MySQL Server | 8.0+ recommended |
| Python package | mysql-connector-python |

## MySQL Setup

Start your MySQL server first. For a local XAMPP/WAMP/MySQL install, the app defaults to:

```text
host: localhost
port: 3306
user: root
password: empty
database: news_fetcher
```

The app creates the `news_fetcher` database and `bookmarks` table automatically on startup.

If your MySQL password or database settings are different, set environment variables before running:

```powershell
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_mysql_password"
$env:MYSQL_DATABASE="news_fetcher"
```

## Install And Run

From this project folder:

```powershell
cd "C:\Users\royal\OneDrive\Documents\PP Projecr"
py -m pip install -r requirements.txt
py main.py
```

## API Key Setup

Set your API key with an environment variable before running:

```powershell
$env:GNEWS_API_KEY="your_gnews_api_key"
$env:NEWS_PROVIDER="gnews"
$env:NEWS_COUNTRY="in"
```

Without a valid API key or internet connection, the app can still show offline demo news, but bookmarks require MySQL to be running.

## Optional Manual Schema Import

The app initializes the database automatically, so this is optional:

```powershell
mysql -u root -p < schema.sql
```
