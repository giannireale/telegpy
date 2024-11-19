# Funzione per inizializzare il webdriver
import asyncio
import os
import re
import sqlite3
import threading
from urllib.parse import urlparse

import aiohttp
import pandas as pd
import requests
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
import sqlite3
import matplotlib.dates as mdates
from datetime import datetime

PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "
INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'
UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"
ASIN_ = "SELECT price FROM asin WHERE asin = ?"
INSERT_ASIN_TO_CHECK = 'INSERT OR IGNORE INTO asin_to_check (asin) VALUES (?)'

api_id = 26761696
api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
phone_number = '+393387203564'
chat_id = "GiovanniReale"  #"290862891"  # Sostituisce con il tuo chat_id

print(api_id)
print(api_hash)
print(phone_number)


#client = TelegramClient('session_name2', api_id, api_hash, )
#client.start(phone_number)


async def get_amazon_price(asin):
    # URL del prodotto Amazon in base all'ASIN
    url = f"https://www.amazon.it/dp/{asin}"

    # Headers per simulare una richiesta da un browser (evita il blocco di bot)
    headers = {
        "User-Agent": UserAgent().random,
        "Accept-Encoding": "gzip, deflate"
    }

    # Effettua la richiesta HTTP
    print(url)
    #session = requests.Session()
    #response = session.get(url, headers=headers, stream=True)
    response = await fetch(url, headers)
    #response = requests.get(url, headers=headers, stream=True)
    #if response.status_code == 200:
    if response:
        # Parsing della pagina HTML
        soup = BeautifulSoup(response, 'html.parser')
        # Prova a trovare il prezzo del prodotto
        try:
            # Questa classe può variare, quindi è necessario controllare il codice sorgente HTML della pagina
            #price = soup.find('span', {'class': 'a-price-whole'}).text
            #price_decimal = soup.find('span', {'class': 'a-price-fraction'}).text
            #full_price = price + price_decimal

            price_element = soup.find('span', {'id': 'priceblock_dealprice'}) or soup.find('span', {
                'id': 'priceblock_ourprice'})
            coupon_element = soup.find('span', {'class': "promoPriceBlockMessage"})
            code_element = soup.find('div', {'id': 'reinvent_price_desktop_pickupOfferDisplay_Desktop'})
            #print(coupon_element)
            #print(code_element)
            price = None

            if price_element:
                # Estrai e converte il prezzo
                price_text = price_element.get_text().strip()
                price = convert_to_float(price_text)
                print(f"Prezzo convertito: {price:.2f} €")
                if price is not None:
                    print(f"Prezzo trovato: {price:.2f} €")
                else:
                    await get_amazon_price(asin)
                    #raise ValueError("Prezzo non convertibile.")
            else:
                div_prezzo = soup.find('div', id='ppd')
                if div_prezzo:
                    full_price = div_prezzo.find('span', {'class': 'a-price-whole'}).text
                    price_decimal = div_prezzo.find('span', {'class': 'a-price-fraction'}).text
                    price = convert_to_float(full_price + price_decimal)
                    print(f"Prezzo trovato alt: {price:.2f} €")
                if price is None:
                    await get_amazon_price(asin)
                    #raise ValueError("Prezzo non trovato.")

            code_match = None
            discount_match = None
            second_label = None
            code_text = None
            coupon_discount = None
            code_discount = None

            # Se è presente un coupon, applica lo sconto
            if coupon_element and price is not None:
                #print(coupon_element.find_all('label'))
                labels = coupon_element.find_all('label')
                if len(labels) >= 2:
                    second_label = labels[1]  # Ricorda che gli indici in Python iniziano da 0
                    #print(second_label.text)
                    discount_match = re.search(r"(\d+(?:,\d+)*)[€%]", second_label.text)
                    #print(discount_match)
                else:
                    second_label = None
            else:
                print("Nessun coupon rilevato.")

            if code_element and price is not None:
                greenbadgepctch = code_element.find_all(id=re.compile(r"^greenBadgepctch"))
                # Stampa gli elementi trovati
                for element in greenbadgepctch:
                    code_text = element.get_text().strip()
                    code_match = re.search(r"(\d+(?:,\d+)*)[€%]", code_text)

            if code_match:
                if '€' in code_text:
                    discount_amount = int(code_match.group(1))
                    code_discount = discount_amount
                    print(
                        f"Codice di {discount_amount}€ rilevato.")
                elif '%' in code_text:
                    discount_percentage = int(code_match.group(1))
                    discount_amount = price * (discount_percentage / 100)
                    code_discount = discount_amount
                    print(
                        f"Codice del {discount_percentage}% rilevato.")
            else:
                print("Impossibile applicare il codice sconto.")

            if discount_match:
                if '€' in second_label.text:
                    discount_amount = int(discount_match.group(1))
                    coupon_discount = discount_amount
                    print(
                        f"Coupon di {discount_amount}€ rilevato.")
                elif '%' in second_label.text:
                    discount_percentage = int(discount_match.group(1))
                    discount_amount = price * (discount_percentage / 100)
                    coupon_discount = discount_amount
                    print(
                        f"Coupon del {discount_percentage}% rilevato.")
            else:
                print("Impossibile applicare il coupon.")

            if code_discount:
                price = price - code_discount
            if coupon_discount:
                price = price - coupon_discount

            print(f"Prezzo finale scontato: {price:.2f} €")
            description = soup.find('span', {'id': 'productTitle'})
            description_text = description.get_text(strip=True)
            if description_text is None or description_text == 'r':
                print("rileggo pagina web description")
                await get_amazon_price(asin)

            brand = soup.select_one('a#bylineInfo')
            brand = brand.text.strip()
            if brand is None:
                print("rileggo pagina web brand vuoto")
                await get_amazon_price(asin)

            # Estrai la categoria
            category = soup.select_one('a.a-link-normal.a-color-tertiary')
            category = category.text.strip()
            if brand is None:
                print("rileggo pagina web category vuoto")
                await get_amazon_price(asin)
            if (description_text == 'r' or price == 'P'):
                print("rileggo pagina web desc vuoto")
                await get_amazon_price(asin)

            print(f"Fine metodo get details {[price, description_text, brand, category]}")
            return [price, description_text, brand, category]

        except requests.exceptions.RequestException as e:
            print(f"Errore durante la richiesta della pagina: {e}")
            await get_amazon_price(asin)
        except ValueError as e:
            print(f"Errore: {e}")
            await get_amazon_price(asin)
        except Exception:
            return "Prezzo non trovato o struttura HTML cambiata"
    else:
        print(f"Errore nella richiesta: {url} - {response}")
        return None


async def fetch(url, headers):
    for _ in range(3):  # Retry up to 3 times
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=60) as response:
                    return await response.text()
        except aiohttp.client_exceptions.ClientConnectionError as e:
            print(f"Connection error: {e}, retrying...")
            await asyncio.sleep(2)  # Wait 2 seconds before retrying
    raise  # Re-raise the exception if all retries fail


async def create_graph(asin, minimum):
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')
    cursor = connection.cursor()
    cursor.execute("SELECT date, price FROM price_history where asin = ?", (asin,))
    data = cursor.fetchall()

    # Estrai le date e i prezzi in liste separate
    dates = [datetime.fromisoformat(row[0]) for row in data]
    prices = [row[1] for row in data]

    # Crea il plot (resto del codice rimane invariato)
    plt.plot(dates, prices, marker='o', linestyle='--')
    plt.xlabel("Data")
    plt.ylabel("Prezzo")
    plt.title("Andamento del prezzo nel tempo del asin " + str(asin))
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    if minimum is not None:  # Aggiungi la linea orizzontale solo se fixed_value è specificato
        plt.axhline(y=minimum, color='r', linestyle='--', label=f'Minimo Amazon: {minimum}')

    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price

    # Crea una lista di tick con la precisione desiderata (es. 2 cifre decimali)
    # Aggiungi un piccolo margine sopra e sotto per una migliore visualizzazione
    yticks = [round(min_price - 0.05 * price_range + i * (1.1 * price_range) / 10, 2) for i in range(11)]

    plt.yticks(yticks)  # Imposta i tick personalizzati

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Formato data-ora
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())  # Posizionamento automatico dei tick
    plt.gcf().autofmt_xdate()  # Ruota le etichette per evitare sovrapposizioni

    plt.savefig('downloaded_images/sinusoidal_graph.png', dpi=300)
    plt.close()


async def aggiorna_prezzo_asin():
    #driver = init_driver()
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')
    cursor = connection.cursor()
    cursor.execute(
        "SELECT asin FROM asin_to_check order BY RANDOM()")  # Sostituisci con il nome della tua tabella

    # Itera sui risultati della query
    for row in cursor.fetchall():
        print('-------------------------------------------------------------------------------------------')
        asin = row[0]  # Estrarre l'ASIN dalla riga
        products = await get_amazon_price(asin)
        await update_price_if_lower_t(True, asin, products[0], products[1], products[2], products[3])
        # Esegui le operazioni desiderate con l'ASIN
        print('-------------------------------------------------------------------------------------------')
    cursor.close()
    connection.close()
    #driver.quit()


async def init_driver():
    os.environ["LANG"] = "it_IT.UTF-8"
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=it-IT")  # Imposta la lingua su italiano
    options.add_argument("--locale=it-IT")  # Imposta il locale su italiano
    options.add_argument(f"--accept-lang=it")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument('--window-position=-32000,-32000')
    options.add_argument('--start-minimized')  # Avvia minimizzato
    options.add_experimental_option('prefs', {'intl.accept_languages': f'it,it-IT'})
    service = Service('C:/driver/chromedriver.exe')
    # Inizializza il driver con il servizio
    ua = UserAgent()
    user_agent = ua.random
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={user_agent}')
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    })
    """)
    driver.minimize_window()
    url = f'https://keepa.com/'
    driver.get(url)
    driver.minimize_window()
    it_div = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@id='currentLanguage']"))
    )
    it_div.click()
    # Attendi che il menu a tendina per la selezione del dominio sia caricato e visibile
    it_domain = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[@rel='domain' and @setting='4']"))
    )
    # Fai clic sull'elemento del dominio ".it"
    it_domain.click()
    it_domain = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[@rel='domain' and @setting='8']"))
    )

    # Fai clic sull'elemento del dominio ".it"
    it_domain.click()
    # URL di Keepa per il prodotto specifico
    #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #driver.minimize_window()
    return driver


#driver = init_driver()


def convert_to_float(price_text):
    """
    Converte una stringa di prezzo in un float, rimuovendo simboli di valuta e gestendo separatori decimali.
    """
    try:
        # Rimuove simboli non numerici (es. valuta) e spazi, e sostituisce la virgola con un punto
        cleaned_price = re.sub(r'[^\d,\.]', '', price_text).replace('.', '').replace(',', '.')
        print(f"Prezzo post conv {cleaned_price}")
        return float(cleaned_price)
    except ValueError:
        print(f"Errore nella conversione del prezzo: '{price_text}'")
        return None


def converti_euro_in_float(stringa_euro):
    try:
        # Rimuovi il simbolo dell'Euro e altri spazi
        stringa_pulita = stringa_euro.replace("€", "").replace(" ", "")

        # Sostituisci la virgola con un punto (per rimuovere i separatori delle migliaia)
        stringa_formattata = stringa_pulita.replace(",", "")

        # Converte la stringa formattata in un numero float
        valore_float = float(stringa_formattata)

        return valore_float
    except ValueError as e:
        print(f"Errore di conversione: {e}")
        return None


async def get_minimum_price_selenium(asin):
    """
    Estrae il prezzo minimo storico da Keepa tramite Selenium.

    :param one_time:
    :param asin: Stringa contenente l'ASIN del prodotto.
    :param driver_path: Il percorso del ChromeDriver.
    :return: Il prezzo minimo storico come stringa.
    """
    global driver_l
    try:
        driver_l = await init_driver()
        driver_l.delete_all_cookies()
        driver_l.execute_script(f"navigator.userAgent = '{UserAgent.getRandom}'")
        driver_l.minimize_window()
        url = f'https://keepa.com/#!product/8-{asin}'
        driver_l.get(url)
        driver_l.minimize_window()
        await asyncio.sleep(1)
        hover_element = WebDriverWait(driver_l, 10).until(EC.presence_of_element_located((By.ID, 'statistics')))
        await asyncio.sleep(1)
        # Simula il passaggio del mouse sopra l'elemento
        action = ActionChains(driver_l)
        action.move_to_element(hover_element).perform()
        # Find the first <tr> element
        await asyncio.sleep(1)
        tr_element = WebDriverWait(driver_l, 10).until(EC.presence_of_element_located((By.XPATH,
                                                                                       "//div[@id='statisticsContent']//table[@id='statsTable']//tbody//tr[2]")))
        # Find the second <td> element within the <tr> element
        td2_element = tr_element.find_element(By.XPATH, "./td[2]")
        if td2_element is None or td2_element.text == '':
            print("td2_element is none")
            td3_element = tr_element.find_element(By.XPATH, "./td[3]")
            td2_text = td3_element.text
        else:
            td2_text = td2_element.text
        print(td2_text.splitlines()[0])
        driver_l.quit()
        print(f"Fine")

        #if(td2_text is None or td2_text == ''):
        #driver_l.quit()
        #await get_minimum_price_selenium(asin)

        return converti_euro_in_float(td2_text.splitlines()[0])
    except Exception as e:
        print(f"Errore durante l'estrazione del prezzo: {e}")
        #amazon_lowest_price = None
        #driver_l.quit()
        #await get_minimum_price_selenium(asin)

    return None


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


async def update_price_if_lower_t(update_price, asin, new_price, text, brand, category):
    # Recupera il prezzo attuale dal database
    print(f"update_price_if_lower_t aggiorna prezzo {update_price}")
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')
    cursor = connection.cursor()
    cursor.execute(ASIN_, (asin,))
    result = cursor.fetchone()

    if result:
        current_price = result[0]
        minimun_price = await get_minimum_price_selenium(asin)
        print(
            f"update_price_if_lower_t result per asin {asin} ({text}) : {result} e new price {new_price} - minimun_price {minimun_price}")
        # Verifica se il nuovo prezzo è un numero e se è minore o uguale al prezzo attuale o al prezzo minimo
        if isinstance(new_price, (int, float)) and (
                new_price < current_price or (minimun_price and new_price <= minimun_price)):
            print(f"update_price_if_lower_t asin trovato {asin}")
            cursor.execute(UPDATE_ASIN, (new_price if update_price else current_price, text, brand, category, asin))
            connection.commit()
            cursor.close()
            connection.close()
            insert_price_history_t(asin, new_price)
            await create_graph(asin, minimun_price)
            print(
                f"Prezzo aggiornato per ASIN {asin} ({text}): {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}  minimo storico {minimun_price}")
            await send_message_to_telegram(chat_id,
                                           f"💣 💣 💣 💣 💣 💣   Prezzo aggiornato per ASIN {asin} ({text}): {current_price} -> {new_price} - https://www.amazon.it/dp/{asin} minimo storico {minimun_price}")
            await send_message_to_telegram('Vik_ing_Re',
                                           f"💣 💣 💣 💣 💣 💣   Prezzo aggiornato per ASIN {asin} ({text}): {current_price} -> {new_price} - https://www.amazon.it/dp/{asin} minimo storico {minimun_price}")

        else:
            print(
                f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price} o {minimun_price} o non è un numero")
    else:
        print(f"ASIN {asin} non trovato nel database")


def extract_asin(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Regex pattern per trovare l'ASIN
    # Cerca uno di questi formati: '/dp/ASIN', '/gp/product/ASIN', '/product/ASIN'
    asin_pattern = r'/dp/([A-Z0-9]{10})|/gp/product/([A-Z0-9]{10})|/product/([A-Z0-9]{10})|/([A-Z0-9]{10})(?=[/?])'

    # Cerca il pattern nel percorso dell'URL
    match = re.search(asin_pattern, parsed_url.path)

    if match:
        # match.group(n) restituirà il gruppo corrispondente, quindi dobbiamo verificare quale gruppo è non-None
        for group in match.groups():
            if group:
                return group
    return None


async def insert_asin_thread(asin, product_name, price, brand, category):
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
    try:
        cursor.execute(INSERT_ASIN, (asin, product_name, price, brand, category))
    except Exception as e:
        print(f"Errore: {e}")
    connection.commit()
    cursor.close()
    connection.close()


#@client.on(events.NewMessage)
async def handler(event):
    print("eccallà")
    if not event.is_channel:
        sender = await event.get_sender()
        sender_name = sender.first_name if sender.first_name else "Sconosciuto"
        print(f"Messaggio da {sender_name}: {event.raw_text} ({event.chat_id})")
        if sender_name == 'G' and event.raw_text.startswith('add'):
            await insert_asin_thread(extract_asin(event.raw_text), 'placeholder', 10000000, 'placeholder',
                                     'placeholder')
            await insert_asin_to_check(extract_asin(event.raw_text))


async def insert_asin_to_check(asin):
    #price_history = get_price_history(asin)
    connection = sqlite3.connect('channels.db', timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')

    cursor = connection.cursor()
    #if price_history:
    # print("Storico Prezzi:")
    # for entry in price_history:
    #    print(f"Data: {entry['date']}, Prezzo: {entry['price']}")
    print(f"insert_asin_to_check {asin}")
    try:
        cursor.execute(INSERT_ASIN_TO_CHECK, [asin])
    except Exception as e:
        print(f"Errore: {e}")
    connection.commit()
    cursor.close()
    connection.close()


async def send_message_to_telegram(c_id, message):
    try:
        client = TelegramClient('session_name2', api_id, api_hash, )
        await client.start(phone_number)
        await client.send_message(c_id, message, file='downloaded_images/sinusoidal_graph.png')
        print("msg inviato")
        client.disconnect()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def infiniteThreading():
    asyncio.run(aggiorna_prezzo_asin())


async def main():
    print(f"Running main loop")
    threads = []
    i = 0

    # Invoca il metodo in thread separati con diversi nomi e ritardi
    while True:
        for i in range(1):
            thread = threading.Thread(target=infiniteThreading, args=())
            threads.append(thread)
            thread.start()

        # Attendi che tutti i thread siano completati
        for thread in threads:
            thread.join()
    #await asyncio.gather(
    #,
    #read_all_channels_recovery()
    #                     ,
    #aggiorna_prezzo_asin()
    #)


#client.loop.run_until_complete(main())
#client.run_until_disconnected()
if __name__ == '__main__':
    asyncio.run(main())
