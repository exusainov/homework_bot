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

TELEGRAM_RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def get_stream_handler() -> logging.Logger:
    """Обработчик логов."""
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s'
        )
    )
    return stream_handler


def get_logger() -> logging.Logger:
    """Обработчик логов."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(get_stream_handler())
    return logger


logger = get_logger()


def send_message(bot, message):
    """Отправляет сообщение."""
    try:
        logger.info('Сообщение отправлено')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError(message):
        logger.error('Ошибка отправки сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    logger.debug('Получение статуса')
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.exceptions.RequestException:
        raise ErrorResponse('Нет ответа от сервера')
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        logger.error(f'Ошибка несоответсвие статуса работы {status_code}')
        raise ValueError(f'Ошибка несоответсвие статуса работы {status_code}')

    return homework_statuses.json()


def check_response(response):
    """Проверяем ответ API."""
    if not response:
        logger.error('Нет ответа', exc_info=True)
        raise ErrorResponse('Нет ответа')
    if not isinstance(response, dict):
        raise TypeError('Нет ответа в словаре')
    if 'homeworks' not in response:
        raise KeyError('Отсуствует ключ')

    if not isinstance(response['homeworks'], list):
        raise TypeError("homework нет в списке")
    if not response['homeworks']:
        raise EmptyList("Список работ пуст")

    logger.debug('Есть ответ от homework')

    return response['homeworks']


def parse_status(homework):
    """Распаковка  ДЗ."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Отсуствует статус или название работы')
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError('Ошибка данного статуса нет в словаре')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    flag = 0
    empty_tokens = []
    for token_name, token in tokens.items():
        if not token:
            empty_tokens.append(token_name)

        else:
            flag += 1
    if flag != len(tokens):
        logger.critical(
            f'Отсутствует обязательная переменная окружения: {empty_tokens}'
        )
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

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            send_message(bot, message)

        finally:
            time.sleep(TELEGRAM_RETRY_TIME)


if __name__ == '__main__':
    if check_tokens():
        main()
    logger.critical('Отсутствует обязательная переменная окружения:')
