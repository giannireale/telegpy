import asyncio
import os
import re
import sqlite3
import time

import requests
from fake_useragent import UserAgent
from langdetect import detect
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telethon import TelegramClient

DB_NAME = 'channels.db'
api_id = 26761696
api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
phone_number = '+393387203564'
chat_id = "GiovanniReale"  #"290862891"  # Sostituisce con il tuo chat_id

print(api_id)
print(api_hash)
print(phone_number)


async def send_message_to_telegram(c_id, message):
    try:
        client = TelegramClient('session_name2', api_id, api_hash, )
        await client.start(phone_number)
        await client.send_message(c_id, message)
        print("msg inviato")
        await client.disconnect()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")



def get_connection():
    """
    Stabilisce una connessione al database SQLite.
    """
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL;')  # Ottimizzazione per concorrenza
    return conn


def create_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS annunci (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          titolo TEXT NOT NULL,
          url TEXT NOT NULL UNIQUE,
          prezzo FLOAT NOT NULL,
          descrizione TEXT NOT NULL
      )
  ''')
    conn.commit()
    conn.close()


# CREATE
def create_annuncio(titolo, url, prezzo, descrizione):
    """
    Crea un nuovo annuncio nel database.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO annunci (titolo, url, prezzo, descrizione)
            VALUES (?, ?, ?, ?)
        ''', (titolo, url, prezzo, descrizione))
        conn.commit()
        return c.lastrowid  # Restituisce l'ID dell'annuncio appena creato
    except sqlite3.IntegrityError as e:
        print(f"Errore durante la creazione: {e}")
        return None
    finally:
        conn.close()


# READ
def get_annuncio_by_id(annuncio_id):
    """
    Recupera un annuncio dal database in base all'ID.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM annunci WHERE id = ?', (annuncio_id,))
    annuncio = c.fetchone()
    conn.close()
    return annuncio


def get_annuncio_by_url(url):
    """
    Recupera un annuncio dal database in base all'url.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM annunci WHERE url = ?', (url,))
    annuncio = c.fetchone()
    conn.close()
    return annuncio


def get_all_annunci():
    """
    Recupera tutti gli annunci dal database.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM annunci')
    annunci = c.fetchall()
    conn.close()
    return annunci


# UPDATE
def update_annuncio(annuncio_id, titolo=None, url=None, prezzo=None, descrizione=None):
    """
    Aggiorna i dati di un annuncio esistente.
    """
    conn = get_connection()
    c = conn.cursor()

    updates = []
    params = []
    if titolo is not None:
        updates.append("titolo = ?")
        params.append(titolo)
    if url is not None:
        updates.append("url = ?")
        params.append(url)
    if prezzo is not None:
        updates.append("prezzo = ?")
        params.append(prezzo)
    if descrizione is not None:
        updates.append("descrizione = ?")
        params.append(descrizione)

    if not updates:
        conn.close()
        return

    query = "UPDATE annunci SET " + ", ".join(updates) + " WHERE id = ?"
    params.append(annuncio_id)

    c.execute(query, params)
    conn.commit()
    conn.close()


# DELETE
def delete_annuncio(annuncio_id):
    """
    Elimina un annuncio dal database.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM annunci WHERE id = ?', (annuncio_id,))
    conn.commit()
    conn.close()


# Initialize table
create_table()


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
    user_agent = ua.chrome
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={user_agent}')
    driver_new = webdriver.Chrome(service=service, options=options)
    driver_new.execute_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    })
    """)
    return driver_new


def check_words_in_text(search_string, text):
    """
    Verifica se una qualsiasi parola della stringa di ricerca è contenuta nel testo.

    :param search_string: La stringa contenente le parole da cercare.
    :param text: Il testo in cui cercare le parole.
    :return: True se almeno una parola della stringa di ricerca è presente nel testo, False altrimenti.
    """
    # Suddividi la stringa di ricerca in parole
    search_words = search_string.split()

    # Suddividi il testo in parole
    text_words = text.split()

    # Verifica se almeno una parola della stringa di ricerca è presente nel testo
    for word in search_words:
        if word in text_words:
            return True

    return False

def convert_to_float(price_text):
    """
    Converte una stringa di prezzo in un float, rimuovendo simboli di valuta e gestendo separatori decimali.
    """
    try:
        # Rimuove simboli non numerici (es. valuta) e spazi, e sostituisce la virgola con un punto
        cleaned_price = re.sub(r'[^\d,\.]', '', price_text).replace('.', '').replace(',', '.')
        #print(f"Prezzo post conv {cleaned_price}")
        return float(cleaned_price)
    except ValueError:
        print(f"Errore nella conversione del prezzo: '{price_text}'")
        return None


nintendo_switch_games_keywords = [
    "Nintendo Switch OLED",
    #"Nintendo Switch OLED usata",
    #"Nintendo Switch OLED nuova",
     #"Nintendo Switch OLED in scatola",
    #"Nintendo Switch OLED con giochi",
    #"Nintendo Switch OLED bundle",
    #"Nintendo Switch OLED a buon prezzo",
    #"Nintendo Switch OLED offerta",
  #  "Nintendo Switch OLED accessori",
  #  "Nintendo Switch OLED controller",
  #  "Nintendo Switch OLED dock",
   # "Nintendo Switch OLED custodia",
    #"Nintendo Switch OLED caricabatterie",
   # "Nintendo Switch OLED power bank",
    #"Nintendo Switch OLED memory card",
    #"Nintendo Switch OLED joystick",
    #"Nintendo Switch OLED grips",
    #"Nintendo Switch OLED adattatore",
    #"Nintendo Switch OLED cavo HDMI",
    #"Nintendo Switch OLED joy-con",
    "Nintendo Switch OLED giochi",
    #"Nintendo Switch OLED Mario Kart",
    #"Nintendo Switch OLED Zelda",
    #"Nintendo Switch OLED Animal Crossing",
    #"Nintendo Switch OLED Super Smash Bros",
    #"Nintendo Switch OLED Pokémon",
    #"Nintendo Switch OLED Splatoon",
    #"Nintendo Switch OLED Minecraft",
    #"Nintendo Switch OLED Fortnite",
    #"Nintendo Switch OLED FIFA",
    #"Nintendo Switch OLED giochi usati",
    #"Nintendo Switch OLED giochi nuovi",
    #"Nintendo Switch OLED giochi in scatola",
    #"Nintendo Switch OLED giochi a buon prezzo",
    #"Nintendo Switch OLED giochi offerta",
    #"Nintendo Switch OLED giochi bundle",
    #"Nintendo Switch OLED giochi multiplayer",
    #"Nintendo Switch OLED giochi single player",
    #"Nintendo Switch OLED giochi RPG",
    #"Nintendo Switch OLED giochi avventura",
    #"Nintendo Switch OLED giochi sport",
    #"Nintendo Switch OLED giochi azione",
    #"Nintendo Switch OLED giochi strategia",
    #"Nintendo Switch OLED giochi puzzle",
    #"Nintendo Switch OLED giochi simulazione",
    #"Nintendo Switch OLED giochi educativi",
    #"Nintendo Switch OLED giochi indie",
    #"Nintendo Switch OLED giochi classici",
    #"Nintendo Switch OLED giochi retro",
    #"Nintendo Switch OLED giochi VR",
    #"Nintendo Switch OLED giochi online",
    #"Nintendo Switch OLED giochi offline",
    #"Nintendo Switch OLED giochi DLC",
    #"Nintendo Switch OLED giochi espansioni",
    #"Nintendo Switch OLED giochi edizioni speciali",
    #"Nintendo Switch OLED giochi edizioni limitate",
    #"Nintendo Switch OLED giochi edizioni collezionisti",
    #"Nintendo Switch OLED giochi edizioni da collezione",
    "Nintendo Switch",
    "Nintendo Switch lite",
    #"Nintendo Switch usata",
    #"Nintendo Switch nuova",
    #"Nintendo Switch in scatola",
    "Nintendo Switch con giochi",
    #"Nintendo Switch bundle",
    #"Nintendo Switch a buon prezzo",
    #"Nintendo Switch offerta",
   # "Nintendo Switch accessori",
   # "Nintendo Switch controller",
   # "Nintendo Switch dock",
   # "Nintendo Switch custodia",
   # "Nintendo Switch caricabatterie",
  #  "Nintendo Switch power bank",
  #  "Nintendo Switch memory card",
    #"Nintendo Switch joystick",
  #  "Nintendo Switch grips",
  #  "Nintendo Switch adattatore",
   # "Nintendo Switch cavo HDMI",
  #  "Nintendo Switch joy-con",

    #"giochi nintendo switch usati",
    #"giochi switch usati",



    # Popolari

    # Età e target
    #"giochi Nintendo Switch bambini",
    #"giochi Nintendo Switch ragazzi",
    # Altre specifiche
    #"giochi Nintendo Switch cartuccia",
    #"switch giochi fisici",

    # Giochi specifici

    # Aggiungi altri titoli popolari qui...
]


def search_keywords_price(pattern):
    """
    Cerca keyword nella tabella prezzi che corrispondono al pattern specificato.

    Args:
        pattern: Il pattern di ricerca (stringa).

    Returns:
        Una lista di tuple, dove ogni tupla rappresenta una riga trovata (keyword, prezzo).
    """

    conn = get_connection()  # Sostituisci con il nome del tuo database
    cursor = conn.cursor()

    query = "SELECT prezzo FROM prezzi WHERE keyword = ?"
    cursor.execute(query, (pattern,))  # Aggiunge % all'inizio e alla fine del pattern

    results = cursor.fetchall()
    #print(results)
    conn.close()
    return results[0]


def rileva_lingua(stringa):
    """
    Rileva la lingua di una stringa utilizzando la libreria langdetect.
    """
    try:
        lingua = detect(stringa)
        return lingua
    except:
        return "Non rilevabile"  #Gestione di errori


page = 1

while True:
    for keyword in nintendo_switch_games_keywords:
        # URL della pagina da raschiare
        soglia = search_keywords_price(keyword)[0]
        url = f"https://www.vinted.it/catalog?search_text={keyword}&order=newest_first&page={page}&currency=EUR&price_to={soglia}"  #&catalog[]=3025&price_to=250
        print(url)
        # Impostazioni del driver
        driver = init_driver()  # Utilizza il driver per Chrome
        driver.minimize_window()
# Apri la pagina
        driver.get(url)
        try:
            # Trova tutti i div con le classi "feed-grid__item" e "feed-grid__item-content"
            grid_items = WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".feed-grid__item"))
            )
        except TimeoutException as e:
            grid_items = []
            #page = 0
        i = 0
        # Itera sui div trovati
        for item in grid_items:
            try:

                # Trova il primo href con la classe "new-item-box__overlay new-item-box__overlay--clickable"
                link = item.find_element(By.CSS_SELECTOR, ".new-item-box__overlay.new-item-box__overlay--clickable")
                href = link.get_attribute("href")
                if get_annuncio_by_url(href) is not None:
                    continue
                if re.search(r"items/\d+-(.*)\?", href):
                    titolo = re.search(r"items/\d+-(.*)\?", href).group(1)
                else:
                    continue

                # Trova il paragrafo con l'attributo data-testid che contiene il prezzo
                price_paragraph = item.find_element(By.CSS_SELECTOR, f"[data-testid$='--price-text']")
                price = price_paragraph.text.strip()

                driver.execute_script("window.open('');")

                # Switch to the new tab
                driver.switch_to.window(driver.window_handles[-1])

                # Navigate to a URL in the new tab
                driver.get(href)
                driver.minimize_window()
                time.sleep(1)
                element = driver.find_element(By.XPATH, '//div[@class="u-text-wrap" and @itemprop="description"]')

                # Extract the text content
                extracted_text = element.text
                if rileva_lingua(extracted_text) == 'de':
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                # Print the extracted text

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                if (
                        (
                        check_words_in_text(keyword, extracted_text)
                        or
                        check_words_in_text(keyword, titolo)
                        )
                        and
                        convert_to_float(price) <= soglia
                        #and get_annuncio_by_url(href) is None
                        #and rileva_lingua(extracted_text) == 'it'
                ):
                    print(f"Link: {href}")
                    print(titolo)
                    print(f"Prezzo: {price}")
                    print(extracted_text)
                    auth_key = 'fb71eae4-f6e5-4372-9905-91bcc41634f9:fx'
                    url = 'https://api-free.deepl.com/v2/translate'
                    params = {
                        'auth_key': auth_key,
                        'text': extracted_text,
                        'target_lang': 'IT'  # Target language (Italian)
                    }

                    create_annuncio(titolo, href, convert_to_float(price), extracted_text)
                    asyncio.run(send_message_to_telegram(chat_id, f"Link: {href} | Titolo: {titolo} | Prezzo: {price} "))
                    asyncio.run(send_message_to_telegram('Vik_ing_Re', f"Link: {href} | Titolo: {titolo} | Prezzo: {price} "))
                    # Send the request
                    #response = requests.post(url, data=params)
                    #result = response.json()

                    # Print the translated text
                    #print(result['translations'][0]['text'])
                    print(
                        "------------------------------------------------------------------------------------------------------------")
                i += 1
                if i >= 3:
                    break

            except Exception as e:
                #print("Errore: ")
                #print(e)
                continue
        #page = page + 1
        driver.quit()

# Chiudi il driver
