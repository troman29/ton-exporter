# ton-exporter

```
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
