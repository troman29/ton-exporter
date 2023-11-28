#!/usr/bin/env python3
import os
import traceback
from datetime import datetime as dt
from typing import List, Optional

import asyncio
from aiohttp import ClientSession
from pydantic import BaseModel
from yaml import load, SafeLoader
from prometheus_client import (
    start_http_server,
    Gauge,
    REGISTRY,
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
)

# Setup metrics
REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)
BALANCE = Gauge('address_balance', 'The balance of the address in the TON blockchain', ['address', 'name'])
TIME_SINCE = Gauge('time_since_last_big_tx', 'Time since the last big transaction', ['address', 'name'])

VALIDATOR_STATUS = Gauge('validator_status', 'Validator status (0 - inactive, 1 - active)', ['address', 'name'])
POOL_STATUS = Gauge('pool_state', 'Pool status (0 - inactive, 1 - pending, 2 - active)', ['address', 'name'])
POOL_DEPOSIT = Gauge('pool_deposit', 'Total deposit of nominators', ['address', 'name'])
CONTROLLER_STATUS = Gauge(
    'controller_state',
    'Controller status (0 - REST, 1 - SENT_BORROWING_REQUEST, 2 - SENT_STAKE_REQUEST,'
    ' 3 - FUNDS_STAKEN, 4 - SENT_RECOVER_REQUEST, 5 - INSOLVENT)',
    ['address', 'name']
)

# Settings
HTTP_PORT = int(os.getenv('HTTP_PORT', 9150))
TON_API_URL = 'https://toncenter.com/api/v2'
ELECTIONS_API_URL = 'https://elections.toncenter.com'
X_API_KEY = os.getenv('TON_X_API_KEY')

MIN_ELECTOR_TX_AMOUNT = 300000
TRANSACTIONS_LIMIT = 50
INTERVAL = 300


# Declare config
class Config(BaseModel):
    class Wallet(BaseModel):
        name: str
        address: str

    class Validator(Wallet):
        pools: Optional[List[str]] = None
        controllers: Optional[List[str]] = None

    wallets: List[Wallet]
    validators: List[Validator]


config: Config
session: ClientSession
active_validators: set[str]


async def main():
    global config
    global session
    global active_validators

    # Parse config
    with open('config.yaml') as file:
        config_dict = load(file.read(), Loader=SafeLoader)

    config = Config(**config_dict)
    session = ClientSession()

    while True:
        try:
            print('\nCollecting metrics...')
            if config.wallets:
                await asyncio.gather(*map(collect_wallet, config.wallets))
            if config.validators:
                active_validators = set(await get_active_validators())
                await asyncio.gather(*map(collect_validator, config.validators))
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(INTERVAL)


async def collect_wallet(wallet: Config.Wallet):
    name = wallet.name
    address = wallet.address
    try:
        # update balance
        balance = round(await get_balance(address))
        BALANCE.labels(address, name).set(balance)

        print(f'{name}:', balance)
    except Exception:
        traceback.print_exc()


async def collect_validator(validator: Config.Validator):
    address = validator.address
    name = validator.name
    pools = validator.pools or []
    controllers = validator.controllers or []

    try:
        # update status
        is_active = address in active_validators

        if pools:
            is_active = pools[0] in active_validators or pools[1] in active_validators
        elif controllers:
            is_active = controllers[0] in active_validators or controllers[1] in active_validators

        VALIDATOR_STATUS.labels(address, name).set(int(is_active))

        # update balance
        balance = round(await get_balance(address))
        BALANCE.labels(address, name).set(balance)

        print(f'{name}:', balance, is_active)
    except Exception:
        traceback.print_exc()

    # Pools and controllers
    validator_name = name.replace('-', '')

    for i, pool in enumerate(pools or []):
        name = f'{validator_name}-pool{i + 1}'
        await collect_pool(name, pool)

    for i, controller in enumerate(controllers or []):
        name = f'{validator_name}-controller{i + 1}'
        await collect_controller(name, controller)


async def collect_pool(name: str, address: str):
    global session
    try:
        # Get transactions
        txs = await get_transactions(address)
        tx = next((x for x in txs if abs(x['amount']) > MIN_ELECTOR_TX_AMOUNT and not x['is_incoming']), None)
        delta_s = int(
            (dt.utcnow() - dt.utcfromtimestamp(tx['timestamp'])).total_seconds()
        ) if tx else 259200
        TIME_SINCE.labels(address, name).set(delta_s)

        # Run get method
        stack = await run_get_method(address, 'get_pool_data')
        state = int(stack[0][1], base=16)
        deposit = round(int(stack[2][1], base=16) / (10 ** 9))

        POOL_STATUS.labels(address, name).set(state)
        POOL_DEPOSIT.labels(address, name).set(deposit)

        print(
            f'{name}:',
            tx and tx['timestamp'],
            tx and dt.utcfromtimestamp(tx['timestamp']),
            delta_s,
            state,
            deposit,
        )
    except Exception:
        traceback.print_exc()
    await asyncio.sleep(0.2)


async def collect_controller(name: str, address: str):
    try:
        stack = await run_get_method(address, 'get_validator_controller_data')
        state = int(stack[0][1], base=16)
        CONTROLLER_STATUS.labels(address, name).set(state)
        print(f'{name}:', state)
    except Exception:
        traceback.print_exc()


async def get_active_validators():
    async with session.get(
        f'{ELECTIONS_API_URL}/getValidationCycles?limit=1&return_participants=true',
        headers={'X-Api-Key': X_API_KEY},
    ) as response:
        raw_validators = (await response.json())[0]['cycle_info']['validators']

    return [x['wallet_address'] for x in raw_validators]


async def run_get_method(address: str, method: str, stack: Optional[List[str]]=None) -> List[str]:
    global session
    async with session.post(
        f'{TON_API_URL}/runGetMethod',
        json={'address': address, 'method': method, 'stack': stack or []},
        headers={'X-Api-Key': X_API_KEY},
    ) as response:
        response.raise_for_status()
        return (await response.json())['result']['stack']


async def get_balance(address: str):
    global session
    async with session.get(
        f'{TON_API_URL}/getWalletInformation?address={address}',
        headers={'X-Api-Key': X_API_KEY},
    ) as response:
        raw_balance = (await response.json())['result']['balance']
    return int(raw_balance) / (10**9)


async def get_transactions(address: str):
    global session
    async with session.get(
        f'{TON_API_URL}/getTransactions?address={address}&limit={TRANSACTIONS_LIMIT}&archival=true',
        headers={'X-Api-Key': X_API_KEY},
    ) as response:
        response.raise_for_status()
        raw_txs = (await response.json())['result']
        return map(parse_raw_tx, raw_txs)


def parse_raw_tx(raw_tx: dict):
    in_msg = raw_tx['in_msg']
    out_msgs = raw_tx['out_msgs']
    amount = float(in_msg['value']) / (10 ** 9)
    for out_msg in out_msgs:
        amount -= float(out_msg['value']) / (10 ** 9)
    is_incoming = not out_msgs
    return {
        'tx_id': f"{raw_tx['transaction_id']['lt']}:{raw_tx['transaction_id']['hash']}",
        'timestamp': int(raw_tx['utime']),
        'amount': amount,
        'fee': raw_tx['fee'],
        'is_incoming': is_incoming,
    }


if __name__ == '__main__':
    start_http_server(HTTP_PORT)

    # Collect metrics in the cycle
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
