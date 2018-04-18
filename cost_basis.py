import os
import datetime
import dateutil.parser
import csv


def is_forked(product):
    # This will determine if the order was a sell and a forked coin
    forked_list = ['BCH', 'BCC', 'BGD']
    return product in forked_list


def get_forked_time(product):
    if product == 'BCH':
        forked_time = '8/17/2018 00:00:00 UTC'
    elif product == 'BGD':
        forked_time = '10/24/2017 00:00:00 UTC'
    else:
        print('Unknown fork product: ' + product)
    return dateutil.parser.parse(forked_time)


def parse_cost_basis_row(row):
    # We want the order to be: [order_time, product, 'buy', cost, amount, cost_per_coin, exchange_currency]
    order = [dateutil.parser.parse(row[0]+" 0:0:0 UTC"), row[2], 'buy', float(row[6]), float(row[1]),
             float(row[6])/float(row[1]), row[4]]
    return order


def parse_cost_basis_file(filename):
    # This function will read in a cost_basis.csv file and output the cost basis (buys)
    # This is based off the csv format given in bitcoin.tax
    # The order should be: Date Volume Symbol Price Currency Fee Cost Source(year bought)
    buys = []
    print('Loading cost basis data from ' + filename)
    # First make sure there are no NULL bytes in the file
    with open(filename, 'rb') as csvfile:
        reader = csv.reader((line.replace('\0', '') for line in csvfile))
        first_row = True
        for row in reader:
            # ignore the header line
            if first_row:
                first_row = False
            elif len(row) > 0:
                save_row = row
                order = parse_cost_basis_row(row)
                buys.append(order)
    print('Done parsing cost basis data!')
    return buys


def get_cost_basis(sells_sorted, buys_sorted, basis_type='highest', tax_year=2017):
    # start_year = dateutil.parser.parse('%d/1/1 00:00:00Z' % tax_year)
    # end_year = dateutil.parser.parse('%d/1/1 00:00:00Z' % (tax_year+1))
    # Set the start of the tax year at Jan 2 because bitcoin.tax uses that
    start_year = dateutil.parser.parse('%d/1/2 00:00:00Z' % tax_year)
    end_year = dateutil.parser.parse('%d/1/2 00:00:00Z' % (tax_year+1))
    full_orders = []
    # Loop through the sell orders and find the best cost basis
    for sell_index in range(len(sells_sorted)):
        sell_time = sells_sorted[sell_index][0]
        product = sells_sorted[sell_index][1]
        # Loop through the buy index to get the cost basis
        # Create a cost basis and subtract sell volume
        # Continue looping until sell volume goes away
        count = 0
        while sells_sorted[sell_index][4] > 0 and count < 1 and (start_year < sell_time < end_year):
            count = 0
            max_cost_index = -1
            max_cost = 0
            max_cost_volume = -1
            for buy_index in range(len(buys_sorted)):
                # See if the buy is the correct product and earlier than the sell time and there are coins left
                if (buys_sorted[buy_index][1] == product) and (sell_time >= buys_sorted[buy_index][0]) and \
                   (buys_sorted[buy_index][4] > 0):
                    cost = buys_sorted[buy_index][5]
                    # See if the max cost is higher
                    if cost > max_cost:
                        max_cost_index = buy_index
                        max_cost = cost
                        max_cost_volume = buys_sorted[buy_index][4]
            # If no cost basis was found, see if the coin was forked
            if max_cost_volume < 0 and is_forked(product):
                print("Found a forked coin")
                print(sells_sorted[sell_index])
                # Set forked coin cost basis (0)
                max_cost = 0
                max_cost_volume = sells_sorted[sell_index][4]
            # See if the max cost volume is still negative
            if max_cost_volume < 0:
                print("WARNING! COULD NOT FIND A COST BASIS FOR sell_index=%d!" % sell_index)
                print(sells_sorted[sell_index])
                count = 1
            else:
                cost_basis_volume = min(max_cost_volume, sells_sorted[sell_index][4])
                # reduce the buy and sell volumes
                # Make sure the max_cost_index is not -1 (forked coin airdrop)
                if max_cost_index >= 0:
                    bought_time = buys_sorted[max_cost_index][0]
                    buys_sorted[max_cost_index][4] = round(buys_sorted[max_cost_index][4] - cost_basis_volume, 8)
                    #cost_basis_per_coin = cost
                    cost_basis_per_coin = max_cost
                else:
                    # This is a forked coin, get the forked date
                    bought_time = get_forked_time(product)
                    cost_basis_per_coin = 0
                sells_sorted[sell_index][4] = round(sells_sorted[sell_index][4] - cost_basis_volume, 8)

                # Full order [description, date acquired, date sold, proceeds, cost basis, gain/loss, datetimebought, datetimesold]
                full_orders.append(['%1.8f ' % cost_basis_volume + product,
                                    bought_time.strftime('%m/%d/%Y'),
                                    sell_time.strftime('%m/%d/%Y'),
                                    cost_basis_volume*sells_sorted[sell_index][5],
                                    cost_basis_volume*cost_basis_per_coin,
                                    cost_basis_volume*(sells_sorted[sell_index][5]-cost_basis_per_coin),
                                    bought_time, sell_time])
    return full_orders
