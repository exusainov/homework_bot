import time
import logging
import os
from dotenv import load_dotenv
import requests
import telegram

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp  # or int(time.time()) вернуть на место
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)

    return homework_statuses.json()


def check_response(response):
    if not response:
        print('da')
        return response

    if 'homeworks' not in response and 'current_date' not in response:
        print('da')

    if type(response.get('homeworks')) != list:
        print('da')

    return response['homeworks']


def parse_status(homework):
    homework_name = homework[0]['homework_name']
    homework_status = homework[0]['status']

    ...

    verdict = HOMEWORK_STATUSES[homework_status]

    ...

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    flag = 0
    for token in tokens:
        if token != '':
            flag += 1
        else:
            return False
    return True


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)  # telegram.
    current_timestamp = 0  # int(time.time()) вернуть обратно

    work_response = get_api_answer(current_timestamp)

    while True:
        try:
            response = check_response(work_response)

            work_status = parse_status(response)
            current_timestamp = 0
            time.sleep(RETRY_TIME)
            # send_message(bot, work_status)  # это времянка
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            send_message(bot, work_status)


if __name__ == '__main__':
    main()
