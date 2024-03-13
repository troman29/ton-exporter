#!/usr/bin/env python3
import sys
import os
import time
import traceback
import socket

from prometheus_client import (
    start_http_server,
    Gauge,
    REGISTRY,
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
)

sys.path.append(os.path.join(sys.path[0], '../mytonctrl'))

from mypylib.mypylib import MyPyClass
from mytoncore.mytoncore import MyTonCore

mytoncore_local = MyPyClass('../mytonctrl/mytoncore/mytoncore.py')
ton = MyTonCore(mytoncore_local)

# Setup metrics
REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)

VALIDATOR_NAME = os.getenv('VALIDATOR_NAME', socket.gethostname())
VALIDATOR_OUT_OF_SYNC = Gauge('validator_out_of_sync', 'Validator synchronization lag', ['name'])

# Settings
HTTP_PORT = int(os.getenv('HTTP_PORT', 9150))
INTERVAL = 30


def main():
    while True:
        try:
            print('\nCollecting metrics...')
            validator_status = ton.GetValidatorStatus()
            VALIDATOR_OUT_OF_SYNC.labels(VALIDATOR_NAME).set(validator_status['outOfSync'])
        except Exception:
            traceback.print_exc()
        time.sleep(INTERVAL)


if __name__ == '__main__':
    start_http_server(HTTP_PORT)
    main()
