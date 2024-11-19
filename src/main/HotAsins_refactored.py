import asyncio
import os
import re
import sqlite3
from urllib.parse import urlparse
from datetime import datetime

import requests
import pandas as pd
import seaborn
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from matplotlib import pyplot as plt
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telethon import TelegramClient, events
import matplotlib.dates as mdates

class DatabaseManager:
    def __init__(self, db_name='channels.db'):
        self.db_name = db_name
        self.connection = None
        self.cursor = None

    async def __aenter__(self):
        self.connection = sqlite3.connect(self.db_name, timeout=10)
        self.connection.execute('PRAGMA journal_mode=WAL;')
        self.cursor = self.connection.cursor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.connection.close()

    async def execute(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.connection.commit()
        return self.cursor.fetchall()

    async def fetchone(self):
        return self.cursor.fetchone()

class AmazonPriceTracker:
    PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "
    INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'
    UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"
    ASIN_ = "SELECT price FROM asin WHERE asin = ?"
    INSERT_ASIN_TO_CHECK = 'INSERT OR IGNORE INTO asin_to_check (asin) VALUES (?)'

    def __init__(self, api_id, api_hash, phone_number, chat_id):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.chat_id = chat_id
        self.client = TelegramClient('session_name2', api_id, api_hash)
        self.client.start(phone_number)
        self.driver = None

    @staticmethod
    def convert_to_float(price_text):
        try:
            cleaned_price = re.sub(r'[^\d,\.]', '', price_text).replace('.', '').replace(',', '.')
            return float(cleaned_price)
        except ValueError:
            print(f"Errore nella conversione del prezzo: '{price_text}'")
            return None

    @staticmethod
    def converti_euro_in_float(stringa_euro):
        try:
            stringa_pulita = stringa_euro.replace("€", "").replace(" ", "")
            stringa_formattata = stringa_pulita.replace(",", "")
            return float(stringa_formattata)
        except ValueError as e:
            print(f"Errore di conversione: {e}")
            return None

    @staticmethod
    def extract_asin(url):
        parsed_url = urlparse(url)
        asin_pattern = r'/dp/([A-Z0-9]{10})|/gp/product/([A-Z0-9]{10})|/product/([A-Z0-9]{10})|/([A-Z0-9]{10})(?=[/?])'
        match = re.search(asin_pattern, parsed_url.path)
        if match:
            for group in match.groups():
                if group:
                    return group
        return None

    async def init_driver(self):
        # ... (codice identico alla funzione originale)
        return driver

    async def get_amazon_price(self, asin):
        # ... (codice identico alla funzione originale)
        print("eee")

    async def get_minimum_price_selenium(self, asin):
        # ... (codice identico alla funzione originale)
        print("eee")
    async def create_graph(self, asin):
        async with DatabaseManager() as db:
            data = await db.execute("SELECT date, price FROM price_history where asin = ?", (asin,))
            # ... (resto del codice per la creazione del grafico)

    async def insert_price_history(self, asin, price):
        async with DatabaseManager() as db:
            await db.execute(self.PRICE_DATE_VALUES_, (asin, price, datetime.now().isoformat()))

    async def update_price_if_lower(self, update_price, asin, new_price, text, brand, category):
        async with DatabaseManager() as db:
            result = await db.execute(self.ASIN_, (asin,))
            # ... (resto del codice per l'aggiornamento del prezzo)

    async def insert_asin(self, asin, product_name, price, brand, category):
        async with DatabaseManager() as db:
            await db.execute(self.INSERT_ASIN, (asin, product_name, price, brand, category))

    async def insert_asin_to_check(self, asin):
        async with DatabaseManager() as db:
            await db.execute(self.INSERT_ASIN_TO_CHECK, [asin])

    async def send_message_to_telegram(self, message):
        try:
            await self.client.send_message(self.chat_id, message, file='downloaded_images/sinusoidal_graph.png')
            print("msg inviato")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    async def aggiorna_prezzo_asin(self):
        while True:
            async with DatabaseManager() as db:
                rows = await db.execute("SELECT asin FROM asin_to_check ORDER BY RANDOM()")
                for row in rows:
                    asin = row[0]
                    products = await self.get_amazon_price(asin)
                    await self.update_price_if_lower(True, asin, products[0], products[1], products[2], products[3])

    @client.on(events.NewMessage)
    async def message_handler(self, event):
        if not event.is_channel:
            sender = await event.get_sender()
            sender_name = sender.first_name if sender.first_name else "Sconosciuto"
            if sender_name == 'G' and event.raw_text.startswith('add'):
                asin = self.extract_asin(event.raw_text)
                await self.insert_asin(asin, 'placeholder', 10000000, 'placeholder', 'placeholder')
                await self.insert_asin_to_check(asin)



async def main():
    # Inizializza la classe con i tuoi dati
    tracker = AmazonPriceTracker(api_id=YOUR_API_ID, api_hash=YOUR_API_HASH, phone_number=YOUR_PHONE_NUMBER,
                                 chat_id=YOUR_CHAT_ID)

    await asyncio.gather(
        tracker.client.run_until_disconnected(),
        tracker.aggiorna_prezzo_asin()
    )

if __name__ == "__main__":
    # Sostituisci con i tuoi dati
    YOUR_API_ID = 26761696
    YOUR_API_HASH = 'b1ead8d774105f6b6eac78412d5988c5'
    YOUR_PHONE_NUMBER = '+393387203564'
    YOUR_CHAT_ID = "GiovanniReale"

    asyncio.run(main())