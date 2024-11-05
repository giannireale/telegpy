import asyncio
import re
import sqlite3
import threading

import requests
from selenium.webdriver import Keys
from telethon import TelegramClient, events, types
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime
import random
import string
from concurrent.futures import ThreadPoolExecutor
from telethon.tl.types import Channel, Message, Chat
import nest_asyncio
from telethon.errors import UsernameInvalidError
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

WHERE_CHANNEL_ID_ = "SELECT enabled FROM channels WHERE channel_id = ?"

WHERE_CHANNEL_ID_MESSAGE = "SELECT channel_name FROM channels WHERE message_recovery = 1"

INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'

UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"

ASIN_ = "SELECT price FROM asin WHERE asin = ?"

NAME_CHANNEL_ID_VALUES_ = 'INSERT OR IGNORE INTO channels (channel_name, channel_id) VALUES (?, ?)'

PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "

# Crea l'event loop di asyncio

#nest_asyncio.apply()
executor = ThreadPoolExecutor(max_workers=5)

# Ottieni questi parametri da https://my.telegram.org
api_id = 26761696
api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
phone_number = '+393387203564'
chat_id = "GiovanniReale"#"290862891"  # Sostituisce con il tuo chat_id

print(api_id)
print(api_hash)
print(phone_number)

conn = sqlite3.connect('channels.db', timeout=10)
conn.execute('PRAGMA journal_mode=WAL;')
c = conn.cursor()
# Creazione della tabella se non esiste
c.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_name TEXT NOT NULL UNIQUE,
        channel_id INTEGER NOT NULL UNIQUE
    )
''')
conn.commit()
c.execute('''
    CREATE TABLE IF NOT EXISTS asin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asin TEXT NOT NULL UNIQUE,
        product_name TEXT NOT NULL,
        price REAL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asin TEXT NOT NULL,
        price FLOAT NOT NULL,
        date DateTime NOT NULL
    )
''')

conn.commit()

#loop = asyncio.get_event_loop()
client = TelegramClient('session_name', api_id, api_hash, )
client_bot = TelegramClient('bot', api_id, api_hash).start(
    bot_token='8054132307:AAECeEAArzTnvOY2SmkJhOWlcaSlWd00ZoU')


def aggiorna_prezzo_asin():
    while True:
        connection = sqlite3.connect('channels.db', timeout=10)
        connection.execute('PRAGMA journal_mode=WAL;')
        cursor = connection.cursor()
        cursor.execute("SELECT asin FROM asin")  # Sostituisci con il nome della tua tabella

        # Itera sui risultati della query
        for row in cursor.fetchall():
            asin = row[0]  # Estrarre l'ASIN dalla riga
            products = get_amazon_price(asin)
            update_price_if_lower_t(True, asin, products[0], products[1], products[2], products[3])
            # Esegui le operazioni desiderate con l'ASIN
        cursor.close()
        connection.close()
        time.sleep(20)


async def aggiorna_prezzo_asin_category():
    while True:
        connection = sqlite3.connect('channels.db', timeout=10)
        connection.execute('PRAGMA journal_mode=WAL;')
        cursor = connection.cursor()
        cursor.execute(
            "SELECT asin FROM asin where category='Informatica'")  # Sostituisci con il nome della tua tabella

        # Itera sui risultati della query
        for row in cursor.fetchall():
            asin = row[0]  # Estrarre l'ASIN dalla riga
            products = get_amazon_price(asin)
            await update_price_if_lower_t(True, asin, products[0], products[1], products[2], products[3])
            # Esegui le operazioni desiderate con l'ASIN
        cursor.close()
        connection.close()
        time.sleep(20)


def insert_price_history(asin, price):
    # Inserisce il record nella tabella price_history
    try:
        c.execute(PRICE_DATE_VALUES_,
                  (asin, price, datetime.now().isoformat()))

        # Conferma le modifiche
        conn.commit()
        #print("Inserimento completato con successo.")
    except sqlite3.Error as e:
        print(f"Errore durante l'inserimento: {e} insert_price_history")


def insert_price_history_t(asin, price):
    # Inserisce il record nella tabella price_history
    try:
        connection = sqlite3.connect('channels.db', timeout=10)
        connection.execute('PRAGMA journal_mode=WAL;')
        cursor = connection.cursor()
        cursor.execute(PRICE_DATE_VALUES_,
                       (asin, price, datetime.now().isoformat()))

        # Conferma le modifiche
        connection.commit()
        cursor.close()
        connection.close()
        #print("Inserimento completato con successo.")
    except sqlite3.Error as e:
        print(f"Errore durante l'inserimento: {e} insert_price_history_t")


def get_amazon_price(asin):
    # URL del prodotto Amazon in base all'ASIN
    url = f"https://www.amazon.it/dp/{asin}"

    # Headers per simulare una richiesta da un browser (evita il blocco di bot)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/58.0.3029.110 Safari/537.3"
    }

    # Effettua la richiesta HTTP
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parsing della pagina HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Prova a trovare il prezzo del prodotto
        try:
            # Questa classe può variare, quindi è necessario controllare il codice sorgente HTML della pagina
            #price = soup.find('span', {'class': 'a-price-whole'}).text
            #price_decimal = soup.find('span', {'class': 'a-price-fraction'}).text
            #full_price = price + price_decimal

            price_element = soup.find('span', {'id': 'priceblock_dealprice'}) or soup.find('span', {
                'id': 'priceblock_ourprice'})
            coupon_element = soup.find(string=lambda text: re.search(r'\d+% coupon', text.lower()) if text else False)
            price = None
            if price_element:
                # Estrai e converte il prezzo
                price_text = price_element.get_text().strip()
                price = convert_to_float(price_text)
                print(f"Prezzo convertito: {price:.2f} €")
                if price is not None:
                    print(f"Prezzo trovato: {price:.2f} €")
                else:
                    raise ValueError("Prezzo non convertibile.")
            else:
                div_prezzo = soup.find('div', id='ppd')
                if div_prezzo:
                    full_price = div_prezzo.find('span', {'class': 'a-price-whole'}).text
                    price_decimal = div_prezzo.find('span', {'class': 'a-price-fraction'}).text
                    print(f"Prezzo trovato pre conversione alt: {full_price + price_decimal} €")
                    price = convert_to_float(full_price + price_decimal)
                    print(f"Prezzo trovato alt: {price:.2f} €")
                if price is None:
                    raise ValueError("Prezzo non trovato.")

            # Se è presente un coupon, applica lo sconto
            if coupon_element and price is not None:
                discount_match = re.search(r'(\d+)%', coupon_element)
                if discount_match:
                    discount_percentage = int(discount_match.group(1))
                    discount_amount = price * (discount_percentage / 100)
                    discounted_price = price - discount_amount
                    price = discounted_price
                    print(
                        f"Coupon del {discount_percentage}% rilevato. Prezzo finale scontato: {discounted_price:.2f} €")
                else:
                    print("Impossibile applicare il coupon.")
            else:
                print("Nessun coupon rilevato.")

            description = soup.find(id='productTitle')
            description_text = description.get_text(strip=True) if description else "Descrizione non trovata"

            brand = soup.select_one('a#bylineInfo')
            brand = brand.text.strip() if brand else 'Marca non trovata'

            # Estrai la categoria
            category = soup.select_one('a.a-link-normal.a-color-tertiary')
            category = category.text.strip() if category else 'Categoria non trovata'
            print(f"Fine metodo get details {[price, description_text, brand, category]}")
            return [price, description_text, brand, category]

        except requests.exceptions.RequestException as e:
            print(f"Errore durante la richiesta della pagina: {e}")
            return "Errore durante la richiesta della pagina"
        except ValueError as e:
            print(f"Errore: {e}")
            return f"Errore: {e}"
        except Exception as e:
            return "Prezzo non trovato o struttura HTML cambiata"
    else:
        print(f"Errore nella richiesta: {response.status_code}")
        return alternative_details(asin)


# Esempio di inserimento di dati
def insert_channel(channel_name, channel_id):
    c.execute(NAME_CHANNEL_ID_VALUES_, (channel_name, channel_id))
    conn.commit()


def convert_to_float(price_text):
    """
    Converte una stringa di prezzo in un float, rimuovendo simboli di valuta e gestendo separatori decimali.
    """
    try:
        # Rimuove simboli non numerici (es. valuta) e spazi, e sostituisce la virgola con un punto
        cleaned_price = re.sub(r'[^\d,\.]', '', price_text).replace(',', '.')
        return float(cleaned_price)
    except ValueError:
        print(f"Errore nella conversione del prezzo: '{price_text}'")
        return None


# Funzione per aggiornare il prezzo se quello nuovo è inferiore a quello attuale
async def update_price_if_lower(asin, new_price, product_title, brand, category):
    # Recupera il prezzo attuale dal database
    c.execute(ASIN_, (asin,))
    result = c.fetchone()

    if result:
        current_price = result[0]
        # Controlla se il nuovo prezzo è inferiore a quello attuale
        if new_price is not None and new_price < current_price:
            #add_to_chart(asin)
            c.execute(UPDATE_ASIN, (new_price, product_title, brand, category, asin))
            insert_price_history(asin, new_price)
            conn.commit()
            print(
                f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")

            message = f"Prezzo aggiornato per ASIN {asin}: {new_price:.2f} € - {product_title}  https://www.amazon.it/dp/{asin}"
            await send_message_to_telegram(chat_id, message)
        #else:
        #print(f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price}")
    else:
        print(f"ASIN {asin} non trovato nel database")


# Funzione per inizializzare il webdriver
def init_driver():
    service = Service('C:/driver/chromedriver.exe')
    # Inizializza il driver con il servizio
    driver = webdriver.Chrome(service=service)
    return driver


def get_asins_from_amazon_search():
    """Funzione per cercare prodotti su Amazon e catturare gli ASIN."""
    search_term = "scheda+video+nvidia+amd+rtx+radeon+gaming+overclocked+economica+editing+video"  # Inserisci il termine di ricerca
    category = "Informatica"  # Categoria opzionale

    driver = init_driver()  # Inizializza il browser
    driver.get("https://www.amazon.it/")  # Vai su Amazon Italia
    time.sleep(3)  # Attendi il caricamento della pagina

    try:
        # Seleziona la categoria (opzionale)
        if category:
            category_dropdown = driver.find_element(By.ID, 'searchDropdownBox')  # Dropdown delle categorie
            category_dropdown.send_keys(category)  # Seleziona la categoria

        # Invia la ricerca nel campo di ricerca
        search_box = driver.find_element(By.ID, "twotabsearchtextbox")
        search_box.send_keys(search_term)
        search_box.send_keys(Keys.RETURN)

        time.sleep(2)  # Attendi il caricamento della pagina dei risultati

        # Recupera tutti gli elementi nella pagina con attributo ASIN
        while True:
            asins = set()  # Usare un set per evitare duplicati
            product_elements = driver.find_elements(By.XPATH, "//div[@data-asin]")

            # Estrai i valori del data-asin
            for product_element in product_elements:
                asin = product_element.get_attribute("data-asin")
                if asin:  # Controlla che asin non sia una stringa vuota
                    asins.add(asin)

            print(f"Trovati {len(asins)} ASINs:")
            for asin in asins:
                try:
                    print(f"\t{asin}")
                    product_detail = get_amazon_price(asin)  # Simula l'ottenimento del prezzo di un prodotto
                    if isinstance(product_detail[0], (float, int)) and isinstance(product_detail[1], str):
                        insert_asin_thread(asin, product_detail[0], product_detail[1], product_detail[2],
                                           product_detail[3])
                except Exception as e:
                    print(f"Errore durante il recupero dei dettagli dell'ASIN {asin}: {e}")

            # Controlla se c'è una pagina successiva
            try:
                next_button = driver.find_element(By.CLASS_NAME, "s-pagination-next")
                if "s-pagination-disabled" in next_button.get_attribute("class"):
                    print("Paginazione conclusa.")
                    break
                else:
                    next_button.click()  # Vai alla pagina successiva
                    time.sleep(2)  # Attendi il caricamento della pagina successiva
            except Exception as e:
                print(f"Errore nel navigare alla pagina successiva: {e}")
                break

    except Exception as e:
        print(f"Errore nel recuperare i prodotti: {e}")
    finally:
        driver.quit()  # Chiudi il browser


async def update_price_if_lower_t(update_price, asin, new_price, text, brand, category):
    # Recupera il prezzo attuale dal database
    print(f"update_price_if_lower_t aggiorna prezzo {update_price}")
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')
    cursor = connection.cursor()
    cursor.execute(ASIN_, (asin,))
    result = cursor.fetchone()
    print(f"update_price_if_lower_t result per asin {asin} ({text}) : {result} e new price {new_price}")
    if result:
        current_price = result[0]
        if new_price is not None and new_price != 'P' and new_price != 'E' and new_price < current_price:
            print(f"update_price_if_lower_t asin trovato {asin}")
            cursor.execute(UPDATE_ASIN, (new_price if update_price else current_price, text, brand, category, asin))
            connection.commit()
            cursor.close()
            connection.close()

            insert_price_history_t(asin, new_price)
            print(
                f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            await send_message_to_telegram(chat_id, f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            #else:
            #print(f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price}")
    else:
        print(f"ASIN {asin} non trovato nel database")


def insert_asin(asin, product_name, price, brand, category):
    print(asin if asin else '' + " " + product_name + " " + price if price else '')
    #price_history = get_price_history(asin)

    #if price_history:
    # print("Storico Prezzi:")
    # for entry in price_history:
    #    print(f"Data: {entry['date']}, Prezzo: {entry['price']}")
    if isinstance(price, str):
        price = 10000000000
    print("insert_asin")
    c.execute(INSERT_ASIN, (asin, product_name, price, brand, category))
    conn.commit()


def insert_asin_thread(asin, product_name, price, brand, category):
    print(asin if asin else '' + " " + product_name + " " + price if price else '')
    #price_history = get_price_history(asin)
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')

    cursor = connection.cursor()
    #if price_history:
    # print("Storico Prezzi:")
    # for entry in price_history:
    #    print(f"Data: {entry['date']}, Prezzo: {entry['price']}")
    if isinstance(price, str):
        price = 10000000000
    print("insert_asin_thread")
    cursor.execute(INSERT_ASIN, (asin, product_name, price, brand, category))
    connection.commit()
    cursor.close()
    connection.close()


def alternative_details(asin):
    # URL del prodotto Amazon in base all'ASIN
    url = "https://www.amazon.it/gp/aws/cart/add-res.html?ASIN.1={asin}&Quantity.1=1"

    # Headers per simulare una richiesta da un browser (evita il blocco di bot)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/58.0.3029.110 Safari/537.3"
    }

    # Effettua la richiesta HTTP
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parsing della pagina HTML
        soup = BeautifulSoup(response.content, 'lxml')

        # Prova a trovare il prezzo del prodotto
        try:
            # Questa classe può variare, quindi è necessario controllare il codice sorgente HTML della pagina
            price = soup.find('span', {'class': 'sc-product-price'}).text
            full_price = price

            description = soup.find('span', {'class': 'sc-product-title'})
            description_text = description.get_text(strip=True) if description else "Descrizione non trovata"

            return [full_price, description_text]
        except Exception as e:
            return "Prezzo non trovato o struttura HTML cambiata"
    else:
        return f"Errore nella richiesta: {response.status_code}"


async def find_and_expand_links(text):
    # Trova tutti i link nel testo
    short_urls = find_links(text)
    # Dizionario per mappare URL corto -> URL espanso
    url_mapping = {url: expand_url(url) for url in short_urls}

    # Sostituisce ogni URL corto con quello espanso nel testo
    for short_url, expanded_url in url_mapping.items():
        asin = extract_asin(expanded_url)
        product_detail = get_amazon_price(asin)

        if not isinstance(product_detail, list):
            product_detail = alternative_details(asin)

        print(product_detail)
        if isinstance(product_detail[0], float) and isinstance(product_detail[1], str):
            insert_asin(asin, product_detail[0], product_detail[1], product_detail[2], product_detail[3])
            await update_price_if_lower(asin, product_detail[0], product_detail[1], product_detail[2],
                                        product_detail[3])
        #add_to_chart(asin)
        text = text.replace(short_url, expanded_url)

    return text


def find_and_expand_links_t(text):
    # Trova tutti i link nel testo
    short_urls = find_links(text)
    #print(short_urls)
    # Dizionario per mappare URL corto -> URL espanso
    url_mapping = {url: expand_url(url) for url in short_urls}
    #print(url_mapping)
    # Sostituisce ogni URL corto con quello espanso nel testo
    for short_url, expanded_url in url_mapping.items():
        asin = extract_asin(expanded_url)
        print(
            asin if asin is not None else 'ASIN NON TROVATO' + " " + expanded_url if expanded_url is not None else 'URL NON TROVATO')
        product_detail = get_amazon_price(asin)

        if not isinstance(product_detail, list):
            product_detail = alternative_details(asin)

        print(f"details async {product_detail}")
        if isinstance(product_detail[0], float) and isinstance(product_detail[1], str):
            insert_asin_thread(asin, product_detail[0], product_detail[1], product_detail[2], product_detail[3])
            update_price_if_lower_t(False, asin, product_detail[0], product_detail[1], product_detail[2],
                                    product_detail[3])
        text = text.replace(short_url, expanded_url)

    return text


def get_channel_id(channel_id):
    try:
        # Connessione al database
        cursor = conn.cursor()

        # Query per selezionare il channel_id
        cursor.execute(WHERE_CHANNEL_ID_, (channel_id,))

        # Ottieni il risultato
        result = cursor.fetchone()

        return result[0] if result else None

    except sqlite3.Error as e:
        print(f"Errore nel database: {e}")
        return None


def find_links(text):
    # Pattern regex per trovare link (http, https, www)
    url_pattern = r'(https?://\S+|www\.\S+)'
    urls = re.findall(url_pattern, text)
    return urls


def expand_url(short_url):
    try:
        response = requests.get(short_url, allow_redirects=True)
        return response.url  # URL finale
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'espansione dell'URL: {e}")
        return None


def extract_asin(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Regex pattern per trovare l'ASIN
    # Cerca uno di questi formati: '/dp/ASIN', '/gp/product/ASIN', '/product/ASIN'
    asin_pattern = r'/dp/([A-Z0-9]{10})|/gp/product/([A-Z0-9]{10})|/product/([A-Z0-9]{10})'

    # Cerca il pattern nel percorso dell'URL
    match = re.search(asin_pattern, parsed_url.path)

    if match:
        # match.group(n) restituirà il gruppo corrispondente, quindi dobbiamo verificare quale gruppo è non-None
        for group in match.groups():
            if group:
                return group
    return None


@client.on(events.NewMessage)
async def handler(event):
    global file
    if event.is_channel:
        if event.message.media:
            # Controlla se l'immagine è un tipo di file supportato
            if hasattr(event.message.media, 'photo'):
                # Scarica l'immagine
                file = await event.message.download_media(file='downloaded_images/')
                print(f"Immagine scaricata: {file}")  # Controlla se il messaggio proviene da un canale
        channel = await event.get_chat()  # Ottiene le informazioni del canale
        channel_name = channel.title if channel.title else "Sconosciuto"
        channel_id = event.chat_id
        print(f"Messaggio dal canale '{channel_name}' (id: {channel_id})")
        insert_channel(event.chat.username, channel_id)
        channel_enabled = get_channel_id(channel_id)
        text_ = await find_and_expand_links(event.raw_text)
        if channel_enabled and channel_enabled == 1:
            print(f"Testo : {text_}")

        if event.buttons:
            for row in event.buttons:  # I pulsanti sono organizzati in righe
                for button in row:
                    if isinstance(button.button, types.KeyboardButtonUrl):
                        url = button.button.url
                        await find_and_expand_links(url)
                        text = button.button.text
                        print(f"Pulsante: {text}, Link: {expand_url(url)}")
    else:
        sender = await event.get_sender()
        sender_name = sender.first_name if sender.first_name else "Sconosciuto"
        print(f"Messaggio da {sender_name}: {event.raw_text}")
    print(f"---------------------------------------------------------------------------------------------")


async def read_all_channels():
    channels = await client.get_dialogs()
    print(f"channels read.")
    # Iterate over the channels
    for channel in channels:
        # Get the channel username
        if channel.entity is not None and not isinstance(channel.entity, Chat):
            channel_username = channel.entity.username
        else:
            channel_username = "Sconosciuto"
        # Get the channel messages
        await get_channel_messages(channel_username)
    print(f"channels ended.")


async def read_all_channels_recovery():
    print(f"channels read.")
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')

    cursor = connection.cursor()
    usernames = cursor.execute(WHERE_CHANNEL_ID_MESSAGE)

    # Iterate over the channels
    for username in usernames:
        # Get the channel messages
        await get_channel_messages(username[0])

    cursor.close()
    connection.close()
    print(f"channels ended.")


async def get_channel_messages(channel_username):
    # Get the channel entity
    channel = await fetch_entity(channel_username)
    print(f"channel: {channel}")
    # Check if the channel is a Channel object
    if not isinstance(channel, Channel):
        print(f"Error: {channel_username} is not a channel.")
        return

    # Get the channel's messages
    messages = await client.get_messages(channel, limit=100000000000)

    # Iterate over the messages
    print("Messaggi: " + str(len(messages)))
    for message in messages:
        # Check if the message is a Message object
        if not isinstance(message, Message):
            continue
        # Print the message text
        #print(message.text)
        find_and_expand_links_t(message.text)
    print("______________________________________________________________________________________")


def run_read_all_channels():
    print("Run read all loop")
    asyncio.run(read_all_channels_recovery())


async def fetch_entity(channel_username):
    try:
        # Try to get the entity (channel, user, etc.)
        entity = await client.get_entity(channel_username)

        if entity is None:
            print(f"Error: No entity found for {channel_username}")
        else:
            print(f"Successfully retrieved entity for {channel_username}")
            # Do something with the entity
            return entity

    except UsernameInvalidError:
        print(f"Error: The username {channel_username} is invalid.")

    except ValueError as e:
        # Handle the case where get_entity cannot map the username
        print(f"ValueError: {e}")

    except TypeError as e:
        # Handle the case where None is returned when a Peer is expected
        print(f"TypeError: {e}")

    except Exception as e:
        # Catch any other exceptions
        print(f"An unexpected error occurred: {e}")


@client_bot.on(events.NewMessage)
async def handler_bot(event):
    sender = await event.get_sender()
    chat_id = event.message.chat_id
    print(f"Il tuo chat ID è: {chat_id}")
    await send_message_to_telegram(chat_id, f"Il tuo chat ID è: {chat_id}")


async def send_message_to_telegram(c_id, message):
    try:
        await client.send_message(c_id, message)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


client.start(phone_number)
client_bot.start()


#8054132307:AAECeEAArzTnvOY2SmkJhOWlcaSlWd00ZoU
# Crea il thread e imposta `daemon=True` per staccarlo
#polling = threading.Thread(target=run_channel, daemon=True)
#infinite = threading.Thread(target=aggiorna_prezzo_asin_category, daemon=True)
# Avvia il thread

#polling.start()
#infinite.start()

#polling.join()
#infinite.join()
#executor.submit(aggiorna_prezzo_asin)
async def main():
    print(f"Running main loop")
    await asyncio.gather(read_all_channels_recovery(), aggiorna_prezzo_asin_category())


client.loop.run_until_complete(main())
client.run_until_disconnected()
client_bot.run_until_disconnected()
#executor.submit(get_asins_from_amazon_search)
#executor.submit(infinite_asin_search)
#create_graph()
