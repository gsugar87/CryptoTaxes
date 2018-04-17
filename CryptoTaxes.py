# This will calculate cryptocurrency taxes based off coinbase, gdax, and bittrex logs
import gdax_reader
import bittrex_reader
import coinbase_reader
import fill_8949
import cPickle as pickle
import os
import turbo_tax
import argparse
import cost_basis
import dateutil.parser
import sys
import copy


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
    # Parse potential inputs
    parser = argparse.ArgumentParser()
    parser.add_argument('-name', default='Full Name', help='Your full name for filling out form 8949.')
    parser.add_argument('-social', default='123456789', help='Your social security number for filling out form 8949.')
    parser.add_argument('-year', type=int, default=2017, help='The tax year you want to fill out.')
    parser.add_argument('-startyear', type=int, default=0, help='The year to start looking for buy orders.  ' +
                                                                'Use this if you have the cost basis for previous ' +
                                                                'years (pass the filename with -costbasis)')
    parser.add_argument('-costbasis', default='', help='An optional file containing the cost basis of coins not ' +
                                                       'included in your GDAX, Coinbase, or Bittrex history.')
    parser.add_argument('--download', action='store_true', help='Use this flag to download the transaction history.  ' +
                                                                'Otherwise the data will be loaded from save.p')
    parser.add_argument('--turbotax', action='store_true', help='Use this flag to make a Turbo Tax txf import file.')
    parser.add_argument('--form8949', action='store_true', help='Use this flag to make the IRS form 8949 pdfs.')
    parser.add_argument('--saveorders', action='store_true', help='Use this flag to save the orders in a Python ' +
                                                                  'pickle file.')
    # Use a preset argument list if using pycharm console
    if 'pydevconsole' in sys.argv[0]:
        args = parser.parse_args([
                                  '-name', "Glenn Sugar",
                                  '-year', '2017',
                                  '-startyear', '2017'])
    else:
        args = parser.parse_args()

    if args.download:
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

        # See if any buy orders should be removed due to startyear input argument
        if args.startyear > 0:
            # Loop through the buys and remove any that are before the startyear
            buys_fixed_startyear = []
            startyear_buys = dateutil.parser.parse('%d/1/2 00:00:00Z' % args.startyear)
            for b in buys_fixed:
                if b[0] >= startyear_buys:
                    buys_fixed_startyear.append(b)
            buys_fixed = buys_fixed_startyear

        # Add cost basis file buys if needed
        if len(args.costbasis) > 0:
            # parse the costbasis file
            other_buys = cost_basis.parse_cost_basis_file(args.costbasis)
            buys_fixed += other_buys
        # sort the buys and sells by date
        print('Sorting the buy and sell orders by time')
        buys_sorted = sorted(buys_fixed, key=lambda buy_order: buy_order[0])
        sells_sorted = sorted(sells_fixed, key=lambda buy_order: buy_order[0])
        # Get the full order information to be used on form 8949 (use list to prevent overwriting buys/sells)
        full_orders = cost_basis.get_cost_basis(copy.deepcopy(sells_sorted), copy.deepcopy(buys_sorted),
                                                basis_type='highest', tax_year=args.year)
        # Save the files in a pickle
        if args.saveorders:
            pickle.dump([buys_sorted, sells_sorted, full_orders], open("save.p", "wb"))
            pickle.dump([buys_sorted, sells_sorted, full_orders, coinbase_buys, coinbase_sells, gdax_buys, gdax_sells,
                         bittrex_buys, bittrex_sells], open("save_everything.p", "wb"))
            print('Orders saved into save.p and save_everything.p')
    else:
        # Load the transaction data
        [buys_sorted, sells_sorted, full_orders] = pickle.load(open("save.p", "rb"))
        print('Buy and sell orders are loaded.')
        # See if any buy orders should be removed due to startyear input argument
        if args.startyear > 0:
            # Loop through the buys and remove any that are before the startyear
            buys_fixed_startyear = []
            startyear_buys = dateutil.parser.parse('%d/1/2 00:00:00Z' % args.startyear)
            for b in buys_sorted:
                if b[0] >= startyear_buys:
                    buys_fixed_startyear.append(b)
            buys_sorted = buys_fixed_startyear
        # See if we should add more buys via a costbasis file
        if len(args.costbasis) > 0:
            # parse the costbasis file
            other_buys = cost_basis.parse_cost_basis_file(args.costbasis)
            buys_sorted += other_buys
            buys_sorted = sorted(list(buys_sorted), key=lambda buy_order: buy_order[0])
        full_orders = cost_basis.get_cost_basis(copy.deepcopy(sells_sorted), copy.deepcopy(buys_sorted),
                                                basis_type='highest', tax_year=args.year)

    # Make the Turbo Tax import file
    if args.turbotax:
        print('Creating the Turbo Tax import file.')
        turbo_tax.make_txf(full_orders)

    # Make the 8949 forms
    if args.form8949:
        print('Creating the 8949 forms.')
        fill_8949.makePDF(full_orders, "test", args.name, args.social)

    # Get the net data (net cost basis, net revenue, net gain/loss
    net_cost = 0
    net_rev = 0
    net_gain = 0
    for o in full_orders:
        net_cost += o[4]
        net_rev += o[3]
        net_gain += o[5]
    print('Done! Net Gain: %1.2f, Net Revenue: %1.2f, Net Cost: %1.2f' % (net_gain, net_rev, net_cost))
