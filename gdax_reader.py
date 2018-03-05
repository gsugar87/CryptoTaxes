# This will read in gdax transactions
import credentials
import GDAX
import dateutil.parser
import datetime
import time


def get_order_ids(history, ignore_products=[]):
    # Loop through the history
    # Transactions are in groups of 100 or less in history (a list of lists)
    # Get all of the order ids
    order_ids = []
    for history_group in history:
        for transaction in history_group:
            if 'order_id' in transaction['details'] and 'product_id' in transaction['details']:
                if transaction['details']['order_id'] not in order_ids and \
                 transaction['details']['product_id'] not in ignore_products:
                    order_ids.append(transaction['details']['order_id'])
            elif 'source' in transaction['details'] and transaction['details']['source'] == 'fork':
                # this was a forked coin deposit
                print(transaction['amount'] + transaction['details']['ticker'] + " obtained from a fork.")
            elif 'transfer_id' not in transaction['details']:
                print("No order_id or transfer_id in details for the following order (WEIRD!)")
                print(transaction)
    return order_ids


def parse_order(order):
    if order['status'] == 'done':
        fees = float(order['fill_fees'])
        buysell = order['side']
        order_time = dateutil.parser.parse(order['done_at'])
        product = order['product_id'][0:order['product_id'].index('-')]
        amount = float(order['filled_size'])
        exchange_currency = order['product_id'][order['product_id'].index('-')+1:]
        if buysell == 'sell':
            cost = float(order['executed_value']) - fees
        else:
            cost = float(order['executed_value']) + fees

        cost_per_coin = cost/amount
    else:
        print('Order status is not done! (WEIRD)')
        print(order)
    return [order_time, product, buysell, cost, amount, cost_per_coin, exchange_currency]


# def parse_coin_coin_order(order):
#     if order['status'] == 'done':
#         fees = float(order['fill_fees'])
#         buysell = order['side']
#         time = dateutil.parser.parse(order['done_at'])
#
#         if buysell == 'sell':
#             cost = float(order['executed_value']) - fees
#         else:
#             cost = float(order['executed_value']) + fees
#     else:
#         print('Order status is not done! (WEIRD)')
#         print(order)
#
#     return [time, order['product_id'], buysell, cost, float(order['filled_size'])]


# get the buys and sells for an account
def get_account_transactions(client, account, ignore_products=[]):
    # Get the account history
    try:
        history = client.getAccountHistory(account['id'])
    except:
        time.sleep(5)
        history = client.getAccountHistory(account['id'])
    # Get all order ids from the account
    order_ids = get_order_ids(history, ignore_products=ignore_products)
    # Get the information from each order_id
    sells = []
    buys = []
    for order_id in order_ids:
        order = parse_order(client.getOrder(order_id))

        if len(order[1]) < 3:
            print('WEIRD ORDER. NO PRODUCT!!!')

        # put order in a buy or sell list
        if order[2] == 'sell':
            sells.append(order)
        elif order[2] == 'buy':
            buys.append(order)
        else:
            print('order is not buy or sell! WEIRD')
            print(order)
    return buys, sells


def get_client():
    client = GDAX.AuthenticatedClient(credentials.gdax_key, credentials.gdax_secret, credentials.gdax_passphrase)
    return client


def get_btc_price(order_time):
    try:
        client = get_client()
        history_btc = client.getProductHistoricRates(product='BTC-USD', start=order_time - datetime.timedelta(hours=1),
                                                     end=order_time)
        bitcoin_price = history_btc[0][4]
    except:
        time.sleep(5)
        client = get_client()
        history_btc = client.getProductHistoricRates(product='BTC-USD', start=order_time - datetime.timedelta(hours=1),
                                                     end=order_time)
        bitcoin_price = history_btc[0][4]
    return bitcoin_price


def get_buys_sells():
    # Get the buys and sells for all orders
    # connect to client first
    print('Connecting to GDAX...')
    client = get_client()
    print('Connected to GDAX!')
    # Get the GDAX accounts
    accounts = client.getAccounts()
    for account in accounts:
        # Only use the USD and BTC accounts since they will contain all transaction ids
        if account['currency'] == 'USD':
            [buys_usd, sells_usd] = get_account_transactions(client, account)
        elif account['currency'] == 'BTC':
            [buys_btc, sells_btc] = get_account_transactions(client, account, ignore_products=['BTC-USD'])
    return buys_usd+buys_btc, sells_usd+sells_btc
