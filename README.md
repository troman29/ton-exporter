# ton-exporter

### Local setup
```shell
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Configurate
export TON_X_API_KEY="<token from https://t.me/tonapibot>"
cp config.example.yaml config.yaml

# Edit config
vim config.yaml

# Run
poetry run python3 ton-exporter.py

# Open browser http://localhost:9150 and see data :)
```

### Install ton-exporter on Linux server
```shell
# Create user
sudo useradd -m prometheus
sudo -i -u prometheus bash

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
git clone https://github.com/troman29/ton-exporter
cd ton-exporter
poetry install

# Setup systemd service
sudo nano /etc/systemd/system/ton-exporter.service
# Paste the contents of the file systemd/ton-exporter.service
sudo systemctl daemon-reload

sudo nano /etc/default/ton-exporter
# Paste env variables

sudo systemctl enable ton-exporter
sudo systemctl start ton-exporter

# Check
sudo systemctl status ton-exporter
curl http://localhost:9150
```

### Install validator-exporter on Linux server
```shell
cd /usr/src
sudo mkdir ton-exporter
sudo chown $USER:$USER ton-exporter

# Install poetry
sudo pip3 install poetry

# Install dependencies
git clone https://github.com/troman29/ton-exporter
cd ton-exporter
poetry install

# Setup systemd service
sudo nano /etc/systemd/system/validator-exporter.service
# Paste the contents of the file systemd/validator-exporter.service
sudo systemctl daemon-reload

sudo systemctl enable validator-exporter
sudo systemctl start validator-exporter

# Check
sudo systemctl status ton-exporter
curl http://localhost:9150
```
