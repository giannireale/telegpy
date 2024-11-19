from telethon import events, TelegramClient


class TeleClient:
    api_id = 26761696
    api_hash = 'b1ead8d774105f6b6eac78412d5988c5'
    phone_number = '+393387203564'
    chat_id = "GiovanniReale"  #"290862891"  # Sostituisce con il tuo chat_id

    print(api_id)
    print(api_hash)
    print(phone_number)

    def __init__(self, session_name):
        self.client = TelegramClient(session_name, self.api_id, self.api_hash, )
        self.client.start(self.phone_number)

    def send_message_to_telegram(self, c_id, message):
        try:
            self.client.send_message(c_id, message)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
