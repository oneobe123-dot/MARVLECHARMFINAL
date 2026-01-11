import os

BOT_TOKEN = os.getenv("8264373358:AAGxrSbdngwsxPjPv24ilWw34MFMYW1xBGs")  # Telegram токен
ADMINS = [int(x) for x in os.getenv("6720495499", "").split("6720495499")]  # ID админов через запятую
START_BALANCE = int(os.getenv("START_BALANCE", 100))
REF_BONUS = int(os.getenv("REF_BONUS", 50))
DAILY_BONUS = int(os.getenv("DAILY_BONUS", 20))
