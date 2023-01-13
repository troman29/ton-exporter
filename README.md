# ton-exporter

### Локальная установка
```shell
# Установим poetry
curl -sSL https://install.python-poetry.org | python3 -

# Установим зависимости (в проекте)
poetry install

# Добавим адреса для мониторинга
export EXPORTER_ADDRESSES="<name1>:<address1>,<name2>:<address2>"
# Пример
export EXPORTER_ADDRESSES="elector:Ef8zMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzM0vF"

# Запустим сервис
poetry run python3 ton-exporter.py

# Открываем в браузере http://localhost:9150 и видим балансы адресов :)
```

### Установка на linux сервер
```shell
# Создадим пользователя
sudo useradd -m prometheus
sudo -i -u prometheus bash

# Установим poetry
curl -sSL https://install.python-poetry.org | python3 -

# Установим зависимости (также будет создан venv)
git clone https://github.com/troman29/ton-exporter
cd ton-exporter
poetry install

# Добавим сервис для автоматического запуска (от вашего юзера)
sudo nano /etc/systemd/system/ton-exporter.service
# Вставьте содержимое systemd/ton-exporter.service
sudo systemctl daemon-reload

sudo nano /etc/default/ton-exporter
# Вставьте переменные окружения (EXPORTER_ADDRESSES="<ваши адреса>")

sudo systemctl enable ton-exporter
sudo systemctl start ton-exporter

# Проверим
sudo systemctl status ton-exporter
curl http://localhost:9150
```
