# This will read in gdax transactions
import credentials
try:
    import gdax
except ImportError:
    import GDAX as gdax
import dateutil.parser
import datetime
import pytz
import time
import cPickle as pickle
import os
from bisect import bisect


# There should only be 4 transaction types, transfer, match, fee, rebate.  We only care about fee and match
good_transaction_types = ['fee', 'match']
# load the bitcoin price history if it exists
if os.path.isfile('bitcoin_history.p'):
    bitcoin_history = pickle.load(open('bitcoin_history.p', 'rb'))
else:
    bitcoin_history = []


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


# get the buys and sells for an account
def get_account_transactions(client, account, ignore_products=[]):
    # Get the account history
    try:
        # history = client.getAccountHistory(account['id'])
        history = client.get_account_history(account['id'])
    except:
        time.sleep(5)
        # history = client.getAccountHistory(account['id'])
        history = client.get_account_history(account['id'])
    # Get all order ids from the account
    order_ids = get_order_ids(history, ignore_products=ignore_products)
    # Get the information from each order_id
    sells = []
    buys = []
    for order_id in order_ids:
        #order = parse_order(client.getOrder(order_id))
        order = parse_order(client.get_order(order_id))

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
    client = gdax.AuthenticatedClient(credentials.gdax_key, credentials.gdax_secret, credentials.gdax_passphrase)
    return client


def get_btc_price(order_time):
    if len(bitcoin_history) == 0:
        try:
            client = get_client()
            #history_btc = client.getProductHistoricRates(product='BTC-USD', start=order_time - datetime.timedelta(hours=1),
            #                                             end=order_time)
            history_btc = client.get_product_historic_rates('BTC-USD', order_time - datetime.timedelta(hours=1), order_time)
            bitcoin_price = history_btc[0][4]
        except:
            time.sleep(5)
            client = get_client()
            history_btc = client.get_product_historic_rates('BTC-USD', order_time - datetime.timedelta(hours=1), order_time)
            bitcoin_price = history_btc[0][4]
    else:
        timestamps = [a[0] for a in bitcoin_history]
        ind = bisect(timestamps, order_time, hi=len(timestamps)-1)
        bitcoin_price = bitcoin_history[ind][1]

    return bitcoin_price


def get_buys_sells():
    # Get the buys and sells for all orders
    # connect to client first
    print('Connecting to GDAX...')
    client = get_client()
    print('Connected to GDAX!')
    # Get the GDAX accounts
    #accounts = client.getAccounts()
    accounts = client.get_accounts()
    # for account in accounts:
    #     # Only use the USD and BTC accounts since they will contain all transaction ids
    #     if account['currency'] == 'USD':
    #         [buys_usd, sells_usd] = get_account_transactions(client, account)
    #     elif account['currency'] == 'BTC':
    #         [buys_btc, sells_btc] = get_account_transactions(client, account, ignore_products=['BTC-USD'])
    # return buys_usd+buys_btc, sells_usd+sells_btc
    return transactions_to_buysells(get_all_transactions(client, accounts))


def get_transactions_from_account(client, account):
    # Get the account history
    try:
        # history = client.getAccountHistory(account['id'])
        history = client.get_account_history(account['id'])
    except:
        time.sleep(5)
        # history = client.getAccountHistory(account['id'])
        history = client.get_account_history(account['id'])
    transactions = []
    for history_group in history:
        for transaction in history_group:
            if transaction['type'] in good_transaction_types:
                # Save this transaction (time, currency, amount changed, order id, trade id)
                transactions.append([dateutil.parser.parse(transaction['created_at']), account['currency'],
                                     float(transaction['amount']), transaction['details']['order_id'],
                                     transaction['details']['trade_id'], transaction['type']])
    return transactions


def get_all_transactions(client, accounts):
    transactions = []
    for account in accounts:
        transactions += get_transactions_from_account(client, account)
    # sort the transactions
    transactions.sort(key=lambda x: x[0])
    return transactions


def transactions_to_buysells(transactions):
    buys = []
    sells = []
    order_transactions = []
    current_order_id = ''
    for transaction in transactions:
        # if current_order_id != transaction[3]:
        if current_order_id != transaction[4]:
            # save the order if it has been created
            if len(order_transactions) > 0:
                sell_amount = 0
                buy_amount = 0
                fee_amount = 0
                fee_product = ''
                for t in order_transactions:
                    order_time = t[0]
                    if t[5] == 'match':
                        if t[2] < 0:
                            sell_amount -= t[2]
                            sell_product = t[1]
                        else:
                            buy_amount += t[2]
                            buy_product = t[1]
                    else:
                        fee_amount += abs(t[2])
                        fee_product = t[1]
                if sell_product == fee_product:
                    sell_amount += fee_amount
                elif buy_product == fee_product:
                    buy_amount -= fee_amount
                # an order: [order_time, product, buysell, cost, amount, cost_per_coin, exchange_currency]
                if buy_product == 'USD':
                    # We sold a coin for USD
                    sells.append([order_time, sell_product, 'sell', buy_amount, sell_amount, buy_amount/sell_amount,
                                  buy_product])
                elif sell_product == 'USD':
                    # We bought a coin using USD
                    buys.append([order_time, buy_product, 'buy', sell_amount, buy_amount, sell_amount/buy_amount,
                                 sell_product])
                elif buy_product == 'BTC':
                    # We sold a coin for BTC
                    sells.append([order_time, sell_product, 'sell', buy_amount, sell_amount, buy_amount/sell_amount,
                                  buy_product])
                elif sell_product == 'BTC':
                    # We bought a coin using BTC
                    buys.append([order_time, buy_product, 'buy', sell_amount, buy_amount, sell_amount/buy_amount,
                                 sell_product])
                else:
                    print('Unknown trading pair!!! Neither BTC nor USD used in the transaction!')
            order_transactions = [transaction]
            # current_order_id = transaction[3]
            current_order_id = transaction[4]
        else:
            # batch the transactions in the order
            order_transactions.append(transaction)

    return buys, sells


# This will get the bitcoin price history
def get_bitcoin_price_history(start_date='2017/1/1', end_date='', save=False):
    client = get_client()
    date = start_date
    bitcoin_history = []
    if isinstance(date, basestring):
        date = dateutil.parser.parse(date)
    if isinstance(end_date, basestring):
        if len(end_date) == 0:
            end_date = datetime.datetime.now()
        else:
            end_date = dateutil.parser.parse(end_date)
    while date < end_date:
        history_btc = client.get_product_historic_rates('BTC-USD', date, date+datetime.timedelta(days=12), 3600)
        while 'message' in history_btc:
            print history_btc['message'] + '  Sleeping for 30 seconds...'
            time.sleep(30)
            history_btc = client.get_product_historic_rates('BTC-USD', date, date+datetime.timedelta(days=12), 3600)
        date = date + datetime.timedelta(days=7)
        for price in history_btc:
            bitcoin_history.append([datetime.datetime.fromtimestamp(price[0], pytz.UTC), price[4]])
    # sort the history
    bitcoin_history.sort(key=lambda x: x[0])
    if save:
        pickle.dump(bitcoin_history, open("bitcoin_history.p", "wb"))
    else:
        return bitcoin_history
