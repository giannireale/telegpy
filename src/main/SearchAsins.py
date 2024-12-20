# Funzione per inizializzare il webdriver
import asyncio
import os
import re
import sqlite3
import time

import aiohttp
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

INSERT_ASIN = 'INSERT INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'


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


def init_driver():
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
    user_agent = ua.browsers
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={user_agent}')
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    })
    """)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.minimize_window()
    return driver


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
            if(description_text == 'r' or price == 'P'):
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


async def get_asins_from_amazon_search():
    """Funzione per cercare prodotti su Amazon e catturare gli ASIN."""

    driver = init_driver()  # Inizializza il browser
    driver.get("https://www.amazon.it/")  # Vai su Amazon Italia
    time.sleep(3)  # Attendi il caricamento della pagina
    category = "Informatica"
    search_terms = [
        "RX 4070 SUPER"
    ]
    try:
        for search_term in search_terms:
            try:
                # Seleziona la categoria (opzionale)
                if category:
                    category_dropdown = driver.find_element(By.ID, 'searchDropdownBox')  # Dropdown delle categorie
                    category_dropdown.send_keys(category)  # Seleziona la categoria

                # Invia la ricerca nel campo di ricerca
                search_box = driver.find_element(By.ID, "twotabsearchtextbox")
                search_box.clear()  # Pulisci il campo di ricerca
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

                    print(f"Trovati {len(asins)} ASINs per '{search_term}':")
                    for asin in asins:
                        try:
                            print(f"\t{asin}")
                            product_detail = await get_amazon_price(
                                asin)  # Simula l'ottenimento del prezzo di un prodotto
                            if isinstance(product_detail[0], (float, int)) and isinstance(product_detail[1], str):
                                await insert_asin_thread(asin, product_detail[1], product_detail[0], product_detail[2],
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
                print(f"Errore nel recuperare i prodotti per '{search_term}': {e}")

    except Exception as e:
        print(f"Errore generale: {e}")
    finally:
        driver.quit()  # Chiudi il browser


async def main():
    print(f"Running main loop")
    await asyncio.gather(
        #read_all_channels_recovery()
        #                     ,
        get_asins_from_amazon_search()
    )


if __name__ == '__main__':
    asyncio.run(
        #read_all_channels_recovery()
        #                     ,
        main()
    )
