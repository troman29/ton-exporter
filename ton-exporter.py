#!/usr/bin/env python3
import asyncio
import os
import traceback
from datetime import datetime as dt

import aiohttp
from prometheus_client import (
    start_http_server,
    Gauge,
    REGISTRY,
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
)

HTTP_PORT = 9150
INTERVAL = 30

VALIDATOR_ADDRESSES = dict([x.split(':') for x in os.getenv('VALIDATOR_ADDRESSES').split(',')])
POOL_ADDRESSES = dict([x.split(':') for x in os.getenv('POOL_ADDRESSES').split(',')])
API_BASE_URL = 'https://toncenter.com/api/v2'
X_API_KEY = os.getenv('TON_X_API_KEY')
MIN_ELECTOR_TX_AMOUNT = 300000

# Setup metrics
REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)
BALANCE = Gauge('address_balance', 'The balance of the address in the TON blockchain', ['address', 'name'])
TIME_SINCE = Gauge('time_since_last_big_tx', 'Time since the last big transaction', ['address', 'name'])
POOL_STATUS = Gauge('pool_state', 'Pool status (0 - inactive, 1 - pending, 2 - active)', ['address', 'name'])


async def main():
    while True:
        print('\nCollecting metrics...')
        async with aiohttp.ClientSession() as session:
            for name, address in POOL_ADDRESSES.items():
                await collect_pool(session, name, address)
            for name, address in VALIDATOR_ADDRESSES.items():
                await collect_validator(session, name, address)
        await asyncio.sleep(INTERVAL)


async def collect_validator(session, name, address):
    try:
        async with session.get(
            f'{API_BASE_URL}/getWalletInformation?address={address}',
            headers={'X-Api-Key': X_API_KEY},
        ) as response:
            raw_balance = (await response.json())['result']['balance']

        balance = round(int(raw_balance) / (10 ** 9))
        BALANCE.labels(address, name).set(balance)
        print(f'{name}:', balance)
    except Exception:
        traceback.print_exc()
    await asyncio.sleep(0.2)


async def collect_pool(session, name, address):
    try:
        async with session.get(
            f'{API_BASE_URL}/getTransactions?address={address}&limit=300&archival=true',
            headers={'X-Api-Key': X_API_KEY},
        ) as response:
            response.raise_for_status()
            txs = map(parse_raw_tx, (await response.json())['result'])
            tx = next((x for x in txs if abs(x['amount']) > MIN_ELECTOR_TX_AMOUNT and not x['is_incoming']), None)
            delta_s = int(
                (dt.utcnow() - dt.utcfromtimestamp(tx['timestamp'])).total_seconds()
            ) if tx else 259200
            TIME_SINCE.labels(address, name).set(delta_s)

        async with session.post(
            f'{API_BASE_URL}/runGetMethod',
            json={'address': address, 'method': 'get_pool_data', 'stack': []},
            headers={'X-Api-Key': X_API_KEY},
        ) as response:
            response.raise_for_status()
            state = int((await response.json())['result']['stack'][0][1], base=16)
            POOL_STATUS.labels(address, name).set(state)

        print(
            f'{name}:',
            tx and tx['timestamp'],
            tx and dt.utcfromtimestamp(tx['timestamp']),
            delta_s,
            state,
        )
    except Exception:
        traceback.print_exc()
    await asyncio.sleep(0.2)


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
