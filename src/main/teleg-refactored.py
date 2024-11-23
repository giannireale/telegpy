import asyncio
import re
import sqlite3
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from telethon import TelegramClient, events, types
from telethon.tl.types import Channel, Message, Chat
import nest_asyncio

# Configure the executor for thread-based tasks
executor = ThreadPoolExecutor(max_workers=5)

# Telegram API credentials
api_id = 26761696
api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
phone_number = '+393387203564'
chat_id = "290862891"  # Your chat_id

# SQLite Database path
DB_PATH = 'channels.db'

# Telegram client setup
client = TelegramClient('session_name', api_id, api_hash)
client_bot = TelegramClient('bot', api_id, api_hash).start(bot_token='8054132307:AAECeEAArzTnvOY2SmkJhOWlcaSlWd00ZoU')

# SQL Queries
INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'
UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"
ASIN_ = "SELECT price FROM asin WHERE asin = ?"
PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "


# Async SQLite Database Connection
async def async_db_connection():
    return sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)


# Utility function to convert a price string to a float
def convert_to_float(price_text):
    try:
        cleaned_price = re.sub(r'[^\d,\.]', '', price_text).replace(',', '.')
        return float(cleaned_price)
    except ValueError:
        print(f"Error converting price: '{price_text}'")
        return None


# Function to fetch product details from Amazon
async def get_amazon_price(asin):
    url = f"https://www.amazon.it/dp/{asin}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/58.0.3029.110 Safari/537.3"
    }

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(executor, requests.get, url, headers)
    price = 1000000000000
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            price_element = soup.find('span', {'id': 'priceblock_dealprice'}) or soup.find('span', {
                'id': 'priceblock_ourprice'})
            coupon_element = soup.find(string=lambda text: re.search(r'\d+% coupon', text.lower()) if text else False)

            if price_element:
                price_text = price_element.get_text().strip()
                price = convert_to_float(price_text)
                if price is None:
                    raise ValueError("Price not convertible.")

            description = soup.find(id='productTitle')
            description_text = description.get_text(strip=True) if description else "Description not found"

            brand = soup.select_one('a#bylineInfo')
            brand = brand.text.strip() if brand else 'Brand not found'

            category = soup.select_one('a.a-link-normal.a-color-tertiary')
            category = category.text.strip() if category else 'Category not found'

            return [price, description_text, brand, category]

        except Exception as e:
            print(f"Error fetching product details: {e}")
            return None
    else:
        print(f"Error in HTTP request: {response.status_code}")
        return None


# Function to insert or update ASIN details in the database
async def insert_or_update_asin(asin, product_name, price, brand, category):
    async with async_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(INSERT_ASIN, (asin, product_name, price, brand, category))
        conn.commit()


# Function to update the price if it's lower and send a Telegram message
async def update_price_if_lower(asin, new_price, product_title, brand, category):
    async with async_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(ASIN_, (asin,))
        result = cursor.fetchone()

        if result:
            current_price = result[0]
            if new_price < current_price:
                cursor.execute(UPDATE_ASIN, (new_price, product_title, brand, category, asin))
                conn.commit()
                await insert_price_history(asin, new_price)
                message = f"Price updated for ASIN {asin}: {new_price:.2f} € - {product_title}"
                await send_message_to_telegram(chat_id, message)


# Function to insert price history
async def insert_price_history(asin, price):
    async with async_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(PRICE_DATE_VALUES_, (asin, price, datetime.now().isoformat()))
        conn.commit()


# Function to expand shortened URLs
async def expand_url(short_url):
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(executor, requests.get, short_url)
        return response.url
    except Exception as e:
        print(f"Error expanding URL: {e}")
        return short_url


# Function to extract ASIN from URL
def extract_asin(url):
    parsed_url = urlparse(url)
    asin_pattern = r'/dp/([A-Z0-9]{10})|/gp/product/([A-Z0-9]{10})|/product/([A-Z0-9]{10})'
    match = re.search(asin_pattern, parsed_url.path)
    if match:
        return next(filter(None, match.groups()), None)
    return None


# Async function to handle new messages from Telegram channels
@client.on(events.NewMessage)
async def new_message_handler(event):
    if event.is_channel:
        channel = await event.get_chat()
        channel_name = channel.title or "Unknown"
        print(f"Message from channel '{channel_name}' (id: {event.chat_id})")

        # Expand and process any links in the message
        expanded_text = await find_and_expand_links(event.raw_text)

        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if isinstance(button.button, types.KeyboardButtonUrl):
                        url = button.button.url
                        expanded_url = await expand_url(url)
                        print(f"Button: {button.button.text}, Link: {expanded_url}")


# Function to find and expand links in the text
async def find_and_expand_links(text):
    short_urls = re.findall(r'(https?://\S+|www\.\S+)', text)
    for short_url in short_urls:
        expanded_url = await expand_url(short_url)
        asin = extract_asin(expanded_url)
        if asin:
            product_detail = await get_amazon_price(asin)
            if product_detail:
                await insert_or_update_asin(asin, product_detail[1], product_detail[0], product_detail[2],
                                            product_detail[3])
                await update_price_if_lower(asin, product_detail[0], product_detail[1], product_detail[2],
                                            product_detail[3])
        text = text.replace(short_url, expanded_url)
    return text


# Function to send a message to a Telegram chat
async def send_message_to_telegram(c_id, message):
    try:
        await client.send_message(c_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")


# Main function to start the Telegram client
async def main():
    print(f"Starting main loop")
    await client.start(phone_number)
    await client_bot.start()
    await client.run_until_disconnected()
    await client_bot.run_until_disconnected()


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
