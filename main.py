import requests
import time

# --- ⚙️ НАЛАШТУВАННЯ ---
TELEGRAM_TOKEN = "8636534241:AAFt9R3cbOdVnh9GpT8MjxwKdfXLqiYtAGk"
CHAT_ID = "-1003749965924"

SYMBOL = "BARDUSDT"
MIN_PRICE = 1.00      # Нижня межа пошуку
MAX_PRICE = 1.1      # Верхня межа пошуку
WALL_THRESHOLD = 1000000  # Мінімальний об'єм, який вважаємо "стіною" (3 млн)
TRIGGER_DROP = 100000     # Тригер падіння (100к)


def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Помилка Telegram: {e}")


def get_all_orders(symbol):

    url = "https://api.bybit.com/v5/market/orderbook"
    # ЗБІЛЬШИЛИ ЛІМІТ ДО 200 (максимум для споту Bybit)
    params = {"category": "spot", "symbol": symbol, "limit": 1000}
    try:
        response = requests.get(url, params=params).json()
        if response["retCode"] == 0:
            bids = response["result"]["b"]
            asks = response["result"]["a"]


            if bids:
                lowest_bid = float(bids[-1][0])
                print(f"🔍 Найглибший ордер, який бачить бот: {lowest_bid}$")

            return bids + asks
    except Exception as e:
        print(f"Помилка Bybit API: {e}")
    return []


def main():
    print(f"🚀 Запуск розумного пошуку стіни для {SYMBOL} в діапазоні {MIN_PRICE}$-{MAX_PRICE}$...")
    send_telegram_alert(
        f"✅ <b>Бот запущено!</b>\nШукаю стіну > {WALL_THRESHOLD:,.0f} на {SYMBOL} в діапазоні {MIN_PRICE} - {MAX_PRICE}$.")

    tracked_price = None
    current_wall_size = 0

    while True:
        orders = get_all_orders(SYMBOL)

        if not orders:
            time.sleep(3)
            continue

        # --- ЕТАП 1: ПОШУК СТІНИ ---
        if tracked_price is None:
            for order in orders:
                price = float(order[0])
                volume = float(order[1])

                # Якщо ціна в нашому діапазоні і об'єм достатньо великий
                if MIN_PRICE <= price <= MAX_PRICE and volume >= WALL_THRESHOLD:
                    tracked_price = price
                    current_wall_size = volume

                    msg = f"🎯 <b>СТІНУ ЗНАЙДЕНО!</b>\nЦіна фіксації: {tracked_price}$\nПочатковий об'єм: {current_wall_size:,.2f}"
                    print(msg)
                    send_telegram_alert(msg)
                    break  # Зупиняємо пошук, бо знайшли ціну

        # --- ЕТАП 2: ВІДСТЕЖЕННЯ ЗНАЙДЕНОЇ СТІНИ ---
        else:
            current_volume = 0

            # Шукаємо поточний об'єм саме на нашій зафіксованій ціні
            for order in orders:
                if float(order[0]) == tracked_price:
                    current_volume = float(order[1])
                    break

            print(f"Моніторинг {tracked_price}$: об'єм {current_volume:,.2f}")

            # Ситуація А: Стіну повністю прибрали (або з'їли)
            if current_volume == 0:
                alert_msg = f"🚨 <b>СТІНА ЗНИКЛА!</b> 🚨\nОрдер по {tracked_price}$ повністю прибрали або виконали!"
                print("⚠️ Стіна зникла!")
                for _ in range(3):
                    send_telegram_alert(alert_msg)
                    time.sleep(0.5)
                tracked_price = None  # Скидаємо ціну і починаємо шукати нову стіну

            # Ситуація Б: Стіну почали розпродавати/відкуповувати (спрацював тригер)
            elif current_wall_size - current_volume >= TRIGGER_DROP:
                alert_msg = (
                    f"🚨 <b>УВАГА! СТІНУ ЇДЯТЬ!</b> 🚨\n\n"
                    f"Ціна: {tracked_price}$\n"
                    f"Було: {current_wall_size:,.2f}\n"
                    f"<b>Стало: {current_volume:,.2f}</b>\n\n"
                    f"🔥 <i>Дій швидко!</i>"
                )
                print("⚠️ Спрацював тригер!")
                for _ in range(3):
                    send_telegram_alert(alert_msg)
                    time.sleep(0.5)
                current_wall_size = current_volume  # Оновлюємо об'єм

            # Ситуація В: Стіна виросла (хтось докинув монет в ордер)
            elif current_volume > current_wall_size:
                current_wall_size = current_volume

        time.sleep(3)  # Пауза перед наступним запитом


if __name__ == "__main__":
    main()