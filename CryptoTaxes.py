# This will calculate cryptocurrency taxes based off coinbase, gdax, and bittrex logs
import gdax_reader
import bittrex_reader
import coinbase_reader
import fill_8949
import cPickle as pickle
import os
import turbo_tax


def fix_orders(orders):
    buys_fixed = []
    sells_fixed = []
    for order in orders:
        # See if the exchange currency is BTC
        if order[6] == 'BTC':
            # This is a coin-coin transaction
            # We need to get the btc value in $$ and create another trade (a sell order)
            bitcoin_price_usd = gdax_reader.get_btc_price(order[0])
            cost_btc = order[3]
            cost_usd = cost_btc * bitcoin_price_usd
            cost_per_coin_usd = cost_usd/order[4]
            # get the coin name
            product = order[1]
            # Fix any coin discrepancies (right now call all bitcoin cash BCH, sometimes it is called BCC)
            if product == 'BCC':
                product = 'BCH'
            if order[2] == 'buy':
                buys_fixed.append([order[0], product, 'buy', cost_usd, order[4], cost_per_coin_usd, 'USD'])
                sells_fixed.append([order[0], 'BTC', 'sell', cost_usd, order[3], bitcoin_price_usd, 'USD'])
            elif order[2] == 'sell':
                sells_fixed.append([order[0], product, 'sell', cost_usd, order[4], cost_per_coin_usd, 'USD'])
                buys_fixed.append([order[0], 'BTC', 'buy', cost_usd, order[3], bitcoin_price_usd, 'USD'])
            else:
                print("WEIRD! Unknown order buy sell type!")
                print(order)
        else:
            # This order was already paid/received with USD
            if order[2] == 'buy':
                buys_fixed.append(order)
            elif order[2] == 'sell':
                sells_fixed.append(order)
            else:
                print("WEIRD! Unknown order buy/sell type!")
                print(order)
    return buys_fixed, sells_fixed


if __name__ == '__main__':
    # Get the user's name and social security number
    print("Starting CryptoTaxes.  This program needs your name and social security number to fill out the IRS form 8949.")
    myname = raw_input("Your full name? ")
    ss = raw_input("Your social? ")

    # Read in the GDAX buys and sells
    gdax_buys, gdax_sells = gdax_reader.get_buys_sells()

    # Read in the Coinbase buys and sells
    coinbase_buys, coinbase_sells = coinbase_reader.get_buys_sells()

    # Read in the Bittrex buys and sells
    bittrex_buys, bittrex_sells = bittrex_reader.get_buys_sells()

    # Go through the buys and sells and see if they are coin-coin transactions
    # Fixed means that coin-coin transactions are now coin-usd, usd-coin
    print('Fixing coin-coin transactions...')
    buys_fixed = []
    sells_fixed = []
    for orders in [coinbase_buys, coinbase_sells, gdax_buys, gdax_sells, bittrex_buys, bittrex_sells]:
        b, s = fix_orders(orders)
        buys_fixed += b
        sells_fixed += s

    # sort the buys and sells by date
    print('Sorting the buy and sell orders by time')
    buys_sorted = sorted(buys_fixed, key=lambda buy_order: buy_order[0])
    sells_sorted = sorted(sells_fixed, key=lambda buy_order: buy_order[0])

    # Get the full order information to be used on form 8949
    full_orders = fill_8949.get_cost_basis(sells_sorted, buys_sorted, basis_type='highest', tax_year=2017)

    # Save the files in a pickle
    #pickle.dump([buys_sorted, sells_sorted, full_orders], open("save.p", "wb"))

    if not os.path.exists("FDFs"):
        os.makedirs("FDFs")
    if not os.path.exists("PDFs"):
        os.makedirs("PDFs")

    # Make the Turbo Tax import file
    turbo_tax.make_txf(full_orders)

    # Make the 8949 forms
    fill_8949.makePDF(full_orders, "test", myname, ss)
