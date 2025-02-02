import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Search Project Gutenberg
def search_gutenberg(query):
    url = f"https://www.gutenberg.org/ebooks/search/?query={query}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    books = []
    for item in soup.select(".booklink"):
        title = item.select_one(".title").text.strip()
        author = item.select_one(".subtitle").text.strip()
        book_id = item.select_one("a")["href"].split("/")[-1]
        download_link = f"https://www.gutenberg.org/ebooks/{book_id}.epub.images"
        books.append(f"📚 *{title}*\n👤 {author}\n⬇️ [Download EPUB]({download_link})")
    return books[:5]

# Search Open Library
def search_open_library(query):
    url = f"https://openlibrary.org/search.json?q={query}"
    res = requests.get(url).json()
    books = []
    for doc in res.get("docs", [])[:5]:
        title = doc.get("title", "N/A")
        author = doc.get("author_name", ["N/A"])[0]
        book_id = doc.get("key", "")
        link = f"https://openlibrary.org{book_id}"
        books.append(f"📚 *{title}*\n👤 {author}\n🔗 [View]({link})")
    return books

# Search Archive.org
def search_archive_org(query):
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": query, "output": "json", "fields": "title,creator,identifier",
        "rows": 5, "mediatype": "texts"
    }
    try:
        res = requests.get(url, params=params).json()
        books = []
        for doc in res.get("response", {}).get("docs", [])[:5]:
            title = doc.get("title", "Untitled")
            author = doc.get("creator", ["Unknown"])[0] if doc.get("creator") else "Unknown"
            identifier = doc.get("identifier", "")
            link = f"https://archive.org/details/{identifier}"
            books.append(f"📚 *{title}*\n👤 {author}\n🔗 [Download]({link})")
        return books
    except:
        return []

# Search Goodreads
def search_goodreads(query):
    url = f"https://www.goodreads.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        books = []
        for item in soup.select(".bookTitle")[:5]:
            title = item.text.strip()
            link = "https://www.goodreads.com" + item["href"]
            author = item.find_next("span", class_="authorName").text.strip()
            books.append(f"📚 *{title}*\n👤 {author}\n🔗 [Goodreads]({link})")
        return books
    except:
        return []

# Pagination
def paginate_results(results, page=1, items_per_page=5):
    start = (page - 1) * items_per_page
    return results[start:start+items_per_page]

def send_page(update, context, results, page=1):
    items_per_page = 5
    total_pages = (len(results) + items_per_page - 1) // items_per_page
    paginated = paginate_results(results, page, items_per_page)
    
    response = f"📚 **Page {page}/{total_pages}**\n\n"
    response += "\n\n".join(paginated)
    
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    if update.callback_query:
        update.callback_query.edit_message_text(response, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)

# Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🔍 Send me a book title/author to search across eBook libraries!")

def search_books(update: Update, context: CallbackContext):
    query = update.message.text
    results = []
    results += search_gutenberg(query)
    results += search_open_library(query)
    results += search_archive_org(query)
    results += search_goodreads(query)
    
    if not results:
        update.message.reply_text("❌ No results found.")
        return
    
    context.user_data["results"] = results
    send_page(update, context, results, page=1)

def page_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    page = int(query.data.split("_")[1])
    results = context.user_data.get("results", [])
    send_page(update, context, results, page)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, search_books))
    dp.add_handler(CallbackQueryHandler(page_callback, pattern="^page_"))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()