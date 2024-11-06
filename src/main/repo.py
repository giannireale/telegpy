def add_to_chart(asin):
    # Configura il WebDriver (ad esempio, ChromeDriver)
    service = Service('C:/driver/chromedriver.exe')

    # Inizializza il driver con il servizio
    driver = webdriver.Chrome(service=service)

    # Naviga alla pagina di login di Amazon
    driver.get(
        'https://www.amazon.it/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.it%2F'
        '%3F_encoding%3DUTF8%26ref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0'
        '%2Fidentifier_select&openid.assoc_handle=itflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F'
        '%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0')
    time.sleep(3)
    # Trova il campo per l'indirizzo email e inserisci l'email
    email_field = driver.find_element(By.ID, 'ap_email')
    email_field.send_keys('giannireale88@gmail.com')
    email_field.send_keys(Keys.RETURN)
    continue_button = driver.find_element(By.ID, 'continue')
    continue_button.click()
    # Attendi un momento per caricare la pagina successiva
    time.sleep(2)

    # Trova il campo per la password e inserisci la password
    password_field = driver.find_element(By.ID, 'ap_password')
    password_field.send_keys('###########')
    password_field.send_keys(Keys.RETURN)
    time.sleep(3)
    sign_button = driver.find_element(By.ID, 'signInSubmit')
    sign_button.click()
    # Attendi per permettere alla pagina di elaborare il login
    time.sleep(3)

    # Verifica se il login è stato completato con successo
    if "Your Account" in driver.page_source:
        print("Login effettuato con successo")
    else:
        print("Login fallito")

    url = f'https://www.amazon.it/dp/{asin}'
    driver.get(url)

    # Attendi che la pagina si carichi completamente
    time.sleep(3)

    # Trova il pulsante 'Aggiungi al carrello' e cliccalo
    try:
        add_to_cart_button = driver.find_element(By.ID, 'add-to-cart-button')
        add_to_cart_button.click()
        print(f"ASIN {asin} aggiunto al carrello con successo.")
    except Exception as e:
        print(f"Errore durante l'aggiunta al carrello: {e}")

    # Chiudi il browser dopo l'operazione
    driver.quit()



    def get_price_history(asin):
        url = f'https://it.camelcamelcamel.com/product/{asin}'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Cerca i dati relativi allo storico dei prezzi
        # Nota: La struttura esatta dipenderà dal layout della pagina di CamelCamelCamel
        price_table = soup.find('table', {'class': 'product_pane'})

        if price_table:
            rows = price_table.find_all('tr')
            price_history = []
            for row in rows:
                columns = row.find_all('td')
                if columns:
                    date = columns[0].get_text(strip=True)
                    price = columns[1].get_text(strip=True)
                    price_history.append({'date': date, 'price': price})
            return price_history
        else:
            print("Impossibile trovare la tabella dei prezzi.")
            return None
    else:
        print(f"Errore: Impossibile accedere alla pagina. Stato: {response.status_code}")
        return None


def create_graph():
    # Creiamo i dati in formato list di tuple, utilizzando solo timestamp e value
    data = [
        ('2024-11-04T09:49:59.580661', 8.2),
        ('2024-11-04T12:23:46.511976', 8.2),
        ('2024-11-04T13:48:06.949058', 8.2),
        ('2024-11-04T14:26:30.082194', 8.2),
        ('2024-11-04T14:26:52.298565', 8.2),
        ('2024-11-04T19:39:39.507804', 8.2),
        ('2024-11-04T19:45:20.807657', 8.2),
        ('2024-11-04T19:46:28.948814', 8.2),
        ('2024-11-04T19:49:24.960759', 8.2),
        ('2024-11-04T19:58:30.423502', 8.2),
        ('2024-11-04T20:00:23.036537', 8.2),
        ('2024-11-04T20:00:36.644777', 8.2),
        ('2024-11-04T21:41:56.983415', 8.2)
    ]

    # Converti i dati in un DataFrame pandas e trasforma il timestamp in un oggetto datetime
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Creazione del grafico temporale usando Seaborn
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='timestamp', y='value', data=df, marker="o")

    # Aggiungi etichette e titolo
    plt.title('Andamento del Valore nel Tempo', fontsize=16)
    plt.xlabel('Timestamp', fontsize=12)
    plt.ylabel('Valore', fontsize=12)

    # Impostare l'orientamento delle etichette sull'asse x per migliorare la leggibilità
    plt.xticks(rotation=45)

    # Mostra il grafico
    plt.tight_layout()
    plt.show()


def extract_prices(text):
    # Regex per trovare i prezzi con formati comuni
    price_pattern = r'(?<!\d)(?:€|£|\$|USD|EUR)?\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s?(?:€|£|\$|USD|EUR)?(?!\d)'

    # Cerca tutte le occorrenze nel testo
    prices = re.findall(price_pattern, text)

    # Rimuovi eventuali separatori di migliaia (es. '1.234,56' diventa '1234,56')
    cleaned_prices = [price.replace('.', '').replace(',', '.') for price in prices]

    return cleaned_prices[0] if (len(cleaned_prices) > 0) else None

def generate_random_asin():
    # L'ASIN ha una lunghezza di 10 caratteri alfanumerici
    prefix = 'B0'  # Gli ASIN recenti iniziano con 'B0'
    remaining_length = 8  # Numero di caratteri rimanenti per l'ASIN
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=remaining_length))
    return prefix + random_part

def infinite_asin_search():
    while True:
        asin = generate_random_asin()
        product_detail = get_amazon_price(asin)
        if isinstance(product_detail[0], float) and isinstance(product_detail[1], str):
            print("if entrato insert")
            insert_asin_thread(asin, product_detail[0], product_detail[1], product_detail[2], product_detail[3])
        time.sleep(2)









        table = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'statsTable')))
    price_element = table.find_elements(By.XPATH, '//tr')
    td_price = price_element.find_elements(By.CSS_SELECTOR, "td[statsRow2]")[0]
    # Trova la riga che contiene il testo "Più basso" nella prima colonna
    #lowest_price_row = driver.find_element(By.XPATH, '//td[contains(text(), "Più basso")]/following-sibling::td[@class="statsRow2"]')

    # Estrarre solo il prezzo, ignorando la data
    amazon_lowest_price = td_price.text.split(' ')[0]  # Prende solo il prezzo, escludendo la parte della data



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
        print(f"update_price_if_lower_t result per asin {asin} ({text}) : {result} e new price {new_price} - minimun_price {minimun_price}")
        if new_price is not None and new_price != 'P' and new_price != 'E' and new_price < current_price or (
                minimun_price and new_price != 'P' and new_price != 'E' and new_price <= minimun_price):
            print(f"update_price_if_lower_t asin trovato {asin}")
            cursor.execute(UPDATE_ASIN, (new_price if update_price else current_price, text, brand, category, asin))
            connection.commit()
            cursor.close()
            connection.close()
            insert_price_history_t(asin, new_price)
            print(
                f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            await send_message_to_telegram(chat_id,
                                           f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            #else:
            #print(f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price}")
    else:
        print(f"ASIN {asin} non trovato nel database")


async def get_asins_from_amazon_search():
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
                    product_detail = await get_amazon_price(asin)  # Simula l'ottenimento del prezzo di un prodotto
                    if isinstance(product_detail[0], (float, int)) and isinstance(product_detail[1], str):
                        await insert_asin_thread(asin, product_detail[0], product_detail[1], product_detail[2],
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