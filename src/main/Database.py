import sqlite3

from src.main.TeleClient import TeleClient


class Database:

    WHERE_CHANNEL_ID_ = "SELECT enabled FROM channels WHERE channel_id = ?"

    WHERE_CHANNEL_ID_MESSAGE = "SELECT channel_name FROM channels WHERE message_recovery = 1"

    INSERT_ASIN = 'INSERT OR IGNORE INTO asin (asin, product_name, price, brand, category) VALUES (?, ?, ?, ?, ?)'

    INSERT_ASIN_TO_CHECK = 'INSERT OR IGNORE INTO asin_to_check (asin) VALUES (?)'

    UPDATE_ASIN = "UPDATE asin SET price = ?, product_name = ?, brand = ?, category = ? WHERE asin = ?"

    ASIN_ = "SELECT price FROM asin WHERE asin = ?"

    NAME_CHANNEL_ID_VALUES_ = 'INSERT OR IGNORE INTO channels (channel_name, channel_id) VALUES (?, ?)'

    PRICE_DATE_VALUES_ = "INSERT INTO price_history (asin, price, date) VALUES (?, ?, ?) "

    def __init__(self):
        self.connection = None
        self.cursor = None

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT NOT NULL UNIQUE,
                channel_id INTEGER NOT NULL UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS asin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL UNIQUE,
                product_name TEXT NOT NULL,
                price REAL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                price FLOAT NOT NULL,
                date DateTime NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS asin_to_check (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL UNIQUE
            )
        ''')
        self.connection.commit()

    def open_connection(self):
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()

    def close_connection(self):
        self.cursor.close()
        self.connection.close()


    async def update_price_if_lower_t(self, update_price, asin, new_price, text, brand, category):
        # Recupera il prezzo attuale dal database
        print(f"update_price_if_lower_t aggiorna prezzo {update_price}")
        self.open_connection()
        self.cursor.execute(self.ASIN_, (asin,))
        result = self.cursor.fetchone()

        if result:
            current_price = result[0]
            minimun_price = await get_minimum_price_selenium(asin)
            print(
                f"update_price_if_lower_t result per asin {asin} ({text}) : {result} e new price {new_price} - minimun_price {minimun_price}")

            # Verifica se il nuovo prezzo è un numero e se è minore o uguale al prezzo attuale o al prezzo minimo
            if isinstance(new_price, (int, float)) and (
                    new_price < current_price or (minimun_price and new_price <= minimun_price)):
                print(f"update_price_if_lower_t asin trovato {asin}")
                self.cursor.execute(self.UPDATE_ASIN, (new_price if update_price else current_price, text, brand, category, asin))
                client = TeleClient("session_name")
                #insert_price_history_t(asin, new_price)
                print(
                    f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")

                await client.send_message_to_telegram("GiovanniReale",
                                               f"Prezzo aggiornato per ASIN {asin}: {current_price} -> {new_price} - https://www.amazon.it/dp/{asin}")
            else:
                print(
                    f"Prezzo non aggiornato per ASIN {asin}: il nuovo prezzo {new_price} non è inferiore a {current_price} o {minimun_price} o non è un numero")
        else:
            print(f"ASIN {asin} non trovato nel database")

        self.close_connection()
