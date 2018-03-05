# This will read in gdax transactions
import credentials
from coinbase.wallet.client import Client
import GDAX
import dateutil.parser
import datetime
import time


def get_client():
    client = Client(credentials.coinbase_key, credentials.coinbase_secret)
    return client


def get_accounts(client):
    accounts = client.get_accounts()
    return accounts


# get the buys and sells for an account
def get_account_transactions(client, account):
    buys = []
    sells = []
    buys_complex = client.get_buys(account['id'])
    sells_complex = client.get_sells(account['id'])
    for order in buys_complex['data']:
        order_time = dateutil.parser.parse(order['payout_at'])
        product = order['amount']['currency']
        cost = float(order['total']['amount'])
        amount = float(order['amount']['amount'])
        cost_per_coin = cost/amount
        exchange_currency = order['total']['currency']
        buys.append([order_time, product, 'buy', cost, amount, cost_per_coin, exchange_currency])
    for order in sells_complex['data']:
        # WARNING! This is not tested since I never sell on coinbase (use GDAX instead!)
        order_time = dateutil.parser.parse(order['payout_at'])
        product = order['amount']['currency']
        cost = float(order['total']['amount'])
        amount = float(order['amount']['amount'])
        cost_per_coin = cost/amount
        exchange_currency = order['total']['currency']
        sells.append([order_time, product, 'sell', cost, amount, cost_per_coin, exchange_currency])
    return buys, sells


def get_buys_sells():
    print('Connecting to Coinbase...')
    client = get_client()
    print('Connected to Coinbase!')
    # Get the Coinbase accounts
    accounts = client.get_accounts()
    buys = []
    sells = []
    for account in accounts['data']:
        # Only use the USD and BTC accounts since they will contain all transaction ids
        if account['currency'] != 'USD':
            buys_dummy, sells_dummy = get_account_transactions(client, account)
            buys += buys_dummy
            sells += sells_dummy
    return buys, sells
