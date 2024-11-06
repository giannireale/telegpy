# Funzione per inizializzare il webdriver
import asyncio
import os
import re
import sqlite3
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telethon import TelegramClient

PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "
INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'
UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"
ASIN_ = "SELECT price FROM asin WHERE asin = ?"

conn = sqlite3.connect('channels.db', timeout=10)
conn.execute('PRAGMA journal_mode=WAL;')
c = conn.cursor()

api_id = 26761696
api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
phone_number = '+393387203564'
chat_id = "GiovanniReale"  #"290862891"  # Sostituisce con il tuo chat_id

print(api_id)
print(api_hash)
print(phone_number)
client = TelegramClient('session_name2', api_id, api_hash, )
client.start(phone_number)


async def get_amazon_price(asin):
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
        except Exception:
            return "Prezzo non trovato o struttura HTML cambiata"
    else:
        print(f"Errore nella richiesta: {response.status_code}")
        return None


async def aggiorna_prezzo_asin():
    while True:
        connection = sqlite3.connect('channels.db', timeout=10)
        connection.execute('PRAGMA journal_mode=WAL;')
        cursor = connection.cursor()
        cursor.execute("SELECT asin FROM asin where category IN ('Informatica','Dispositivi Amazon & Accessori', 'Elettronica', 'Videogiochi', 'Categoria non trovata') order BY RANDOM()")  # Sostituisci con il nome della tua tabella

        # Itera sui risultati della query
        for row in cursor.fetchall():
            asin = row[0]  # Estrarre l'ASIN dalla riga
            products = await get_amazon_price(asin)
            await update_price_if_lower_t(True, asin, products[0], products[1], products[2], products[3])
            # Esegui le operazioni desiderate con l'ASIN
        cursor.close()
        connection.close()
        time.sleep(20)


def init_driver():
    os.environ["LANG"] = "it_IT.UTF-8"
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=it-IT")  # Imposta la lingua su italiano
    options.add_argument("--locale=it-IT")  # Imposta il locale su italiano
    options.add_argument(f"--accept-lang=it")
    options.add_argument('--window-position=-32000,-32000')
    options.add_argument('--start-minimized')  # Avvia minimizzato
    options.add_experimental_option('prefs', {'intl.accept_languages': f'it,it-IT'})
    service = Service('C:/driver/chromedriver.exe')
    # Inizializza il driver con il servizio
    driver = webdriver.Chrome(service=service, options=options)
    driver.minimize_window()
    return driver


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

    :param asin: Stringa contenente l'ASIN del prodotto.
    :param driver_path: Il percorso del ChromeDriver.
    :return: Il prezzo minimo storico come stringa.
    """
    # Inizializza il driver di Selenium
    driver = init_driver()
    try:

        url = f'https://keepa.com/#!product/8-{asin}'
        driver.get(url)
        time.sleep(1)
        it_div = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='currentLanguage']"))
        )
        it_div.click()
        time.sleep(1)
        # Attendi che il menu a tendina per la selezione del dominio sia caricato e visibile
        it_domain = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@rel='domain' and @setting='4']"))
        )
        # Fai clic sull'elemento del dominio ".it"
        it_domain.click()
        time.sleep(1)
        it_domain = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@rel='domain' and @setting='8']"))
        )

        # Fai clic sull'elemento del dominio ".it"
        it_domain.click()
        time.sleep(1)
        # URL di Keepa per il prodotto specifico

        hover_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'statistics')))

        # Simula il passaggio del mouse sopra l'elemento
        action = ActionChains(driver)
        action.move_to_element(hover_element).perform()
        time.sleep(1)
        # Find the first <tr> element
        tr_element = driver.find_element(By.XPATH,
                                         "//div[@id='statisticsContent']//table[@id='statsTable']//tbody//tr[2]")
        # Find the first <td> element within the <tr> element
        td1_element = tr_element.find_element(By.XPATH, "./td[1]")

        # Find the second <td> element within the <tr> element
        td2_element = tr_element.find_element(By.XPATH, "./td[2]")
        if td2_element is None or td2_element.text == '':
            print("td2_element is none")
            td3_element = tr_element.find_element(By.XPATH, "./td[3]")
            td2_text = td3_element.text
        else:
            td2_text = td2_element.text
        print(td2_text.splitlines()[0])
        return converti_euro_in_float(td2_text.splitlines()[0])
    except Exception as e:
        print(f"Errore durante l'estrazione del prezzo: {e}")
        amazon_lowest_price = None
    finally:
        # Chiude il browser
        driver.quit()

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
            print(
                f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            await send_message_to_telegram(chat_id,
                                           f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin} minimo storico {minimun_price}")
        else:
            print(
                f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price} o {minimun_price} o non è un numero")
    else:
        print(f"ASIN {asin} non trovato nel database")


async def send_message_to_telegram(c_id, message):
    try:
        await client.send_message(c_id, message)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def main():
    print(f"Running main loop")
    await asyncio.gather(
        #read_all_channels_recovery()
        #                     ,
        aggiorna_prezzo_asin()
    )


client.loop.run_until_complete(main())
client.run_until_disconnected()
