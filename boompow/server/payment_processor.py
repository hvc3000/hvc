#!/usr/bin/env python

import re
import argparse
import redis
import requests
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from bpow import Validations

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), db=3, port=6379, decode_responses=True)

parser = argparse.ArgumentParser()
parser.add_argument('--node', type=str, default='http://[::1]:7072')
parser.add_argument('--wallet', type=str, help="BANANO node wallet.", default='1234')
parser.add_argument('--account', type=str, help='Account from which to send funds.', default='ban_1boompow14irck1yauquqypt7afqrh8b6bbu5r93pc6hgbqs7z6o99frcuym')
parser.add_argument('--set-prize-pool', type=int, help='Set prize pool amount', default=None)
parser.add_argument('--dry_run', action='store_true', help='Perform everything except sending funds, for debugging.')
args = parser.parse_args()

if args.set_prize_pool:
    print(f"Setting prize pool to {args.set_prize_pool}")
    r.set("bpow:prizepool", str(args.set_prize_pool))
    exit(0)
elif not Validations.validate_address(args.account):
    print("Invalid payout address specified")
    exit(1)

MAX_PRIZE_POOL = 10000

prize_pool = r.get("bpow:prizepool")
# There's a MAX_PAYOUT_FACTOR to avoid someone from fat fingering the change
prize_pool = min(float(prize_pool), MAX_PRIZE_POOL) if prize_pool is not None else 0
print(f"Paying ~{prize_pool} TOTAL BANANO")

clients = r.smembers("clients")
clients = {c for c in clients}

final_payout_sum = 0

# Setup logging
LOG_FILE = '/tmp/bpow_payments.log'
logger = logging.getLogger()
def setup_logger():
    logging.basicConfig(level=logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s@%(funcName)s:%(lineno)s", "%Y-%m-%d %H:%M:%S %z")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

setup_logger()

def communicate_wallet(wallet_command) -> dict:
    try:
        r = requests.post(args.node, json=wallet_command, timeout=300)
        return r.json()
    except requests.exceptions.RequestException:
        return None

class ClientStats():
    def __init__(self, client: str, total_pows: int, pow_delta: int, total_paid: float):
        self.client = client
        self.total_pows = total_pows
        self.total_paid = total_paid
        self.pow_delta = pow_delta


def send(destination : str, amount_ban : float) -> str:
    """Send amount to destination, return hash. None if failed"""
    expanded = float(amount_ban) * 100
    amount_raw = str(int(expanded) * (10 ** 27))
    action = {
        "action": "send",
        "wallet": args.wallet,
        "source": args.account,
        "destination": destination,
        "amount": amount_raw
    }
    resp = communicate_wallet(action)
    if resp is not None and 'block' in resp:
        return resp['block']
    return None

total_pows = 0
clients_to_evaluate = []
for client in clients:
    if not Validations.validate_address(client):
        logger.info(f"!Skipping client '{client}' as it is an invalid BANANO account!\n\n")
        continue
    client_info = r.hgetall(f"client:{client}")
    if not client_info:
        continue

    # Sum total work contributions for  this client
    total_works = 0
    total_works += int(client_info['precache']) if 'precache' in client_info else 0
    total_works += int(client_info['ondemand']) if 'ondemand' in client_info else 0

    # Get how many pows this client has already been paid for
    total_credited = int(client_info['total_credited']) if 'total_credited' in client_info else 0
    total_paid = float(client_info['total_paid']) if 'total_paid' in client_info else 0.0

    # Get how many pow this client has contributed in this current cycle
    total_pow_client = total_works - total_credited
    total_pows += total_pow_client

    if total_pow_client < 0:
        logger.error(f"Skipping client, bad state: client has total_works < total_credited {client}")
        continue
    elif total_pow_client == 0:
        continue

    client_stats = ClientStats(client, total_works, total_pow_client, total_paid)
    clients_to_evaluate.append(client_stats)

for c in clients_to_evaluate:
    percent_of_total = round(c.pow_delta / total_pows, 6)
    payment_amount = round(percent_of_total * prize_pool, 2)
    if payment_amount <= 0:
        continue
    logger.info(f"Sending {payment_amount} ({percent_of_total * 100}%) to {c.client}")
    if not args.dry_run:
        send_resp = send(c.client, payment_amount)
        if send_resp is not None:
            r.hset(f"client:{c.client}", 'total_credited', str(c.total_pows))
            r.hset(f"client:{c.client}", 'total_paid', str(payment_amount + c.total_paid))
            final_payout_sum += payment_amount
            logger.info(f"Block Hash: {send_resp}")
        else:
            logger.error("PAYMENT FAILED, RPC SEND RETURNED NULL")
    else:
        logger.info("Skipping, dry run")
        final_payout_sum  += payment_amount

total_paid_db = r.get('bpow:totalrewards')
total_paid_db = float(total_paid_db) if total_paid_db is not None else 0.0

total_paid_db += final_payout_sum

r.set('bpow:totalrewards', str(total_paid_db))

logger.info(f"Total paid today {final_payout_sum}, total paid all time {total_paid_db}")
