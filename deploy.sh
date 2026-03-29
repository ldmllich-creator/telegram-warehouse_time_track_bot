#!/bin/bash
# =============================================================
# Автоматический деплой Telegram Time Tracking Bot
# =============================================================
# Использование: 
#   1. Скопируйте этот файл на сервер
#   2. Запустите: bash deploy.sh
# =============================================================

set -e

echo "=========================================="
echo "  Деплой Telegram Time Tracking Bot"
echo "=========================================="

# 1. Обновление системы и установка Docker
echo ""
echo ">>> 1/5 Установка Docker..."
if command -v docker &> /dev/null; then
    echo "Docker уже установлен ✅"
else
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    echo "Docker установлен ✅"
fi

# 2. Клонирование репозитория
echo ""
echo ">>> 2/5 Клонирование репозитория..."
cd /opt
if [ -d "telegram-bot" ]; then
    echo "Папка уже существует, обновляю..."
    cd telegram-bot
    git pull
else
    git clone https://github.com/ldmllich-creator/telegram-warehouse_time_track_bot.git telegram-bot
    cd telegram-bot
fi
echo "Репозиторий готов ✅"

# 3. Проверка credentials.json (сначала ищем в /root/)
echo ""
echo ">>> 3/5 Проверка credentials.json..."
if [ ! -f credentials.json ] && [ -f /root/credentials.json ]; then
    cp /root/credentials.json ./credentials.json
    echo "credentials.json скопирован из /root/ ✅"
elif [ -f credentials.json ]; then
    echo "credentials.json найден ✅"
else
    echo ""
    echo "❌ ВАЖНО: Файл credentials.json не найден!"
    echo "Скопируйте его на сервер:"
    echo "  scp credentials.json root@<IP>:/opt/telegram-bot/"
    echo "Затем запустите скрипт повторно."
    exit 1
fi

# 4. Настройка .env
echo ""
echo ">>> 4/5 Настройка переменных окружения..."
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Введите данные:"
    echo ""
    read -p "BOT_TOKEN: " BOT_TOKEN
    read -p "GOOGLE_SHEETS_ID: " GOOGLE_SHEETS_ID
    cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
GOOGLE_SHEETS_ID=${GOOGLE_SHEETS_ID}
GOOGLE_CREDENTIALS_JSON_PATH=credentials.json
EOF
    echo ".env создан ✅"
else
    echo ".env уже существует ✅"
fi

# 5. Запуск бота
echo ""
echo ">>> 5/5 Запуск бота..."
docker compose down 2>/dev/null || true
docker compose up -d --build

echo ""
echo "=========================================="
echo "  ✅ Бот успешно запущен!"
echo "=========================================="
echo ""
echo "Полезные команды:"
echo "  docker compose logs -f     — смотреть логи"
echo "  docker compose restart     — перезапустить"
echo "  docker compose down        — остановить"
echo ""
