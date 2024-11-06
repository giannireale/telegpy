import asyncio
import re

import requests
from bs4 import BeautifulSoup


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


asyncio.run(get_amazon_price('B0CWQ7TK7Q'))
