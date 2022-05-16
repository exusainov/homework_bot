import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import EmptyList, ErrorResponse

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60  # после тестов вернуть 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

_log_format = f"%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"


def get_stream_handler():
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(get_stream_handler())
    return logger


logger = get_logger()


def send_message(bot, message):
    try:
        logger.info('Сообщение отправлено')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Ошибка отправки сообщения')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    logger.debug('Получение статуса')
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.exceptions.RequestException:
        raise
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        logger.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    return homework_statuses.json()


def check_response(response):

    # if not response:
    #    logger.error(f'Отсутствует домашняя работа:')
    #    return response

    # if 'homeworks' not in response and 'current_date' not in response:
    #    logger.error(f'Отсутствует обязательных ключей:')

    # if type(response.get('homeworks')) != list:
    #    logger.error(f'Домашняя работа не является списком:')
    if len(response) == 0:
        logger.error('Нет ответа')
        raise ErrorResponse('Нет ответа')
    if not isinstance(response, dict):
        raise TypeError('Нет ответа в словаре')
    try:
        homeworks = response['homeworks']
    except KeyError as e:
        logger.error('Key Error', e)
    if not isinstance(homeworks, list):
        raise TypeError("homework нет в списке")
    if len(homeworks) == 0:
        raise EmptyList("Empty list")

    logger.debug('Есть ответ от homework')

    return response['homeworks']


def parse_status(homework):
    homework_name = homework['homework_name']
    homework_status = homework['status']

    ...

    verdict = HOMEWORK_STATUSES[homework_status]

    ...

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    flag = 0
    for token_name, token in tokens.items():
        if not token:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token_name}'
            )
        else:
            flag += 1
    if flag != len(tokens):
        return False
    return True


def main():
    """Основная логика работы бота."""

    logger.info("Программа стартует")

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    check_tokens()

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
