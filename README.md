# Tarot Answer Bot

Telegram-бот для автоматизации гаданий на Таро.

## Что умеет MVP

- Принимает текстовые и голосовые сообщения оператора.
- Извлекает вопрос клиента через Gemini.
- Подтверждает вопрос через inline-кнопки.
- Создаёт и выбирает клиента.
- Хранит имя, возраст, общий контекст и историю гаданий в SQLite.
- Выбирает 3 карты Таро случайным образом.
- Генерирует ответ в стиле гадания.
- Обновляет профиль клиента только устойчивыми фактами.
- Поддерживает запуск через `systemd`.
- Содержит workflow для CI и автодеплоя на Raspberry Pi.

## Структура

- `tarot_answer_bot/` - код бота, сервисы, модели и промпты.
- `tests/` - базовые тесты.
- `systemd/` - пример unit-файла.
- `.github/workflows/ci.yml` - CI/CD.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Инициализируйте базу и запустите бота:

```bash
python -m tarot_answer_bot.main
```

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота.
- `GEMINI_API_KEY` - ключ Gemini API.
- `DATABASE_URL` - строка подключения к SQLite.
- `GEMINI_MODEL` - модель Gemini, по умолчанию `gemini-2.0-flash`.
- `VOICE_MODEL_SIZE` - размер модели Whisper для распознавания речи.
- `ALLOW_REVERSED_CARDS` - разрешить перевёрнутые карты.

## systemd

Пример unit-файла лежит в `systemd/tarot-bot.service`.

Схема запуска на Raspberry Pi:

1. Разместить проект, например, в `/opt/tarot-bot`.
2. Создать виртуальное окружение.
3. Установить зависимости.
4. Скопировать unit-файл в `/etc/systemd/system/tarot-bot.service`.
5. Выполнить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tarot-bot
sudo systemctl start tarot-bot
```

## CI/CD

Workflow:

- на `pull_request` и `push` выполняются `python -m compileall`, `ruff check`, `pytest`;
- на `push` в `main` после успешной проверки запускается deploy job на self-hosted runner;
- deploy job делает `git pull`, обновляет зависимости и перезапускает `systemd`-сервис.

## Примечание

Распознавание речи вынесено в отдельный модуль. Для продакшена на Raspberry Pi стоит проверить, что выбранная модель Whisper реально тянется по ресурсам устройства.
