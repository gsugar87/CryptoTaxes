# This will read in bittrex transactions
# Note that you must supply the fullOrders.csv file
# This only works with BTC transactions!!!!
import csv
import dateutil.parser


def parse_order(order):
    # Get the currency
    product = order[1][order[1].index('-')+1:]
    amount = float(order[3])
    fees = float(order[5])
    if 'SELL' in order[2]:
        buysell = 'sell'
        cost = float(order[6])-fees
    elif 'BUY' in order[2]:
        buysell = 'buy'
        cost = float(order[6])+fees
    else:
        print('UNKNOWN BUY/SELL ORDER!!')
        print(order)
    cost_per_coin = cost/amount
    exchange_currency = order[1][0:order[1].index('-')]
    order_time = dateutil.parser.parse(order[8] + " UTC")
    return [order_time, product, buysell, cost, amount, cost_per_coin, exchange_currency]


def get_buys_sells(order_file='fullOrders.csv'):
    # Get the buys and sells for all orders
    buys = []
    sells = []
    print('Loading Bittrex orders from ' + order_file)
    # First make sure there are no NULL bytes in the file
    with open(order_file, 'rb') as csvfile:
        reader = csv.reader((line.replace('\0', '') for line in csvfile))
        first_row = True
        for row in reader:
            # ignore the header line
            if first_row:
                first_row = False
            elif len(row) > 0:
                save_row = row
                order = parse_order(row)
                if order[2] == 'buy':
                    buys.append(order)
                elif order[2] == 'sell':
                    sells.append(order)
                else:
                    print("WEIRD! Order is neither buy nor sell!")
                    print(order)
    print('Done parsing Bittrex orders!')
    return buys, sells
