#!/usr/bin/env python3
import asyncio
import os
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
API_BASE_URL = 'https://toncenter.com/api/v2'
INTERVAL = 30
ADDRESSES = dict([x.split(':') for x in os.getenv('TON_ADDRESSES').split(',')])


async def main():
    while True:
        await collect_metrics()
        await asyncio.sleep(INTERVAL)


async def collect_metrics():
    print('\nCollecting metrics...')
    async with aiohttp.ClientSession() as session:
        for name, address in ADDRESSES.items():
            try:
                async with session.get(f'{API_BASE_URL}/getWalletInformation?address={address}') as response:
                    raw_balance = (await response.json())['result']['balance']
                    balance = round(int(raw_balance) / (10 ** 9))
                    BALANCE.labels(address, name).set(balance)
                    print(f'{name}:', balance)
            except Exception as e:
                print(e)
            await asyncio.sleep(1.1)


if __name__ == '__main__':
    # Setup metrics
    REGISTRY.unregister(GC_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(PROCESS_COLLECTOR)
    BALANCE = Gauge('address_balance', 'The balance of the address in the TON blockchain', ['address', 'name'])
    start_http_server(HTTP_PORT)
    # Collect metrics in the cycle
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
