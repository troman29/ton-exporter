#!/usr/bin/env python3
import asyncio
import os
import traceback
from datetime import datetime

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

BALANCE_ADDRESSES = dict([x.split(':') for x in os.getenv('BALANCE_ADDRESSES').split(',')])
POOL_ADDRESSES = dict([x.split(':') for x in os.getenv('POOL_ADDRESSES').split(',')])
API_BASE_URL = 'https://toncenter.com/api/v2'
X_API_KEY = os.getenv('TON_X_API_KEY')
BIG_TX_AMOUNT = 300000


async def main():
    while True:
        await collect_metrics()
        await asyncio.sleep(INTERVAL)


async def collect_metrics():
    print('\nCollecting metrics...')
    async with aiohttp.ClientSession() as session:
        for name, address in BALANCE_ADDRESSES.items():
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

        for name, address in POOL_ADDRESSES.items():
            try:
                async with session.get(
                    f'{API_BASE_URL}/getTransactions?address={address}&limit=300&archival=true',
                    headers={'X-Api-Key': X_API_KEY},
                ) as response:
                    response.raise_for_status()
                    txs = map(parse_raw_tx, (await response.json())['result'])
                    tx = next((x for x in txs if abs(x['amount']) > BIG_TX_AMOUNT), None)
                    delta_s = (
                        datetime.utcnow() - datetime.fromtimestamp(tx['timestamp'])
                    ).seconds if tx else 259200  # 3 days
                    TIME_SINCE.labels(address, name).set(delta_s)
                    print(f'{name}:', tx, delta_s)
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
    # Setup metrics
    REGISTRY.unregister(GC_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(PROCESS_COLLECTOR)
    BALANCE = Gauge('address_balance', 'The balance of the address in the TON blockchain', ['address', 'name'])
    TIME_SINCE = Gauge('time_since_last_big_tx', 'Time since the last big transaction', ['address', 'name'])
    start_http_server(HTTP_PORT)

    # Collect metrics in the cycle
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
