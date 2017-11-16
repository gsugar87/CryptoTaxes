# This script should read in all the tax information on GDAX and Coinbase
import GDAX
import numpy as np
import time
import requests.packages.urllib3
import datetime
import pytz
import dateutil.parser
from coinbase.wallet.client import Client
import copy
import os
import credentials

# Disable the urllib3 annoying warnings
requests.packages.urllib3.disable_warnings()

myname = raw_input("Your full name? ")
ss = raw_input("Your social? ")

# Connect to the GDAX Client
print('Connecting to GDAX...')
publicClient = GDAX.PublicClient()
authClient = GDAX.AuthenticatedClient(credentials.gdaxKey, credentials.gdaxSecret, credentials.gdaxPassphrase)
print('Connected to GDAX!')

print('Connecting to Coinbase...')
coinbaseClient = Client(credentials.coinbaseKey, credentials.coinbaseSecret)
print('Connected to Coinbase!')
print('Downloading Coinbase accounts...')
cbAcntBtc = coinbaseClient.get_account("BTC")
cbAcntEth = coinbaseClient.get_account("ETH")
cbAcntLtc = coinbaseClient.get_account("LTC")
print('Coinbase accounts downloaded!')

api_url = 'https://api.gdax.com/'

# Get the GDAX address IDs
print('Downloading GDAX accounts...')
gdaxAccounts =authClient.getAccounts()
for account in gdaxAccounts:
    if account['currency'] == 'USD':
        gdaxUsdAddress = account['id']
    elif account['currency'] == 'BTC':
        gdaxBtcAddress = account['id']
    elif account['currency'] == 'LTC':
        gdaxLtcAddress = account['id']
    elif account['currency'] == 'ETH':
        gdaxEthAddress = account['id']
    else:
        print('Unknown currency in GDAX accounts!  ' + account['currency'])

# Get the account histories
btcHistory = authClient.getAccountHistory(gdaxBtcAddress)
ethHistory = authClient.getAccountHistory(gdaxEthAddress)
ltcHistory = authClient.getAccountHistory(gdaxLtcAddress)
usdHistory = authClient.getAccountHistory(gdaxUsdAddress)
print('GDAX accounts downloaded!')

# GDAX account histories are weird, they are in groups of 100
btcGroup = len(btcHistory)-1
ethGroup = len(ethHistory)-1
ltcGroup = len(ltcHistory)-1
usdGroup = len(usdHistory)-1
btcIndex = len(btcHistory[btcGroup])-1
ethIndex = len(ethHistory[ethGroup])-1
ltcIndex = len(ltcHistory[ltcGroup])-1
usdIndex = len(usdHistory[usdGroup])-1

# get the orders
btcOrder = btcHistory[btcGroup][btcIndex]
ethOrder = ethHistory[ethGroup][ethIndex]
ltcOrder = ltcHistory[ltcGroup][ltcIndex]
usdOrder = usdHistory[usdGroup][usdIndex]


# Define a useful function to decrement the index and deal with the weird grouping
def decrementIndex(index, group, history):
    index -= 1
    if index < 0:
        group -= 1
        if group < 0:
            return -1, -1
        index = len(history[group]) - 1
    return index, group


# make sure the orders have an order id
while 'order_id' not in btcOrder['details']:
    [btcIndex, btcGroup] = decrementIndex(btcIndex, btcGroup, btcHistory)
    btcOrder = btcHistory[btcGroup][btcIndex]
while 'order_id' not in ethOrder['details']:
    [ethIndex, ethGroup] = decrementIndex(ethIndex, ethGroup, ethHistory)
    ethOrder = ethHistory[ethGroup][ethIndex]
while 'order_id' not in ltcOrder['details']:
    [ltcIndex, ltcGroup] = decrementIndex(ltcIndex, ltcGroup, ltcHistory)
    ltcOrder = ltcHistory[ltcGroup][ltcIndex]

# get the orders
btcOrderInfo = authClient.getOrder(btcOrder['details']['order_id'])
ethOrderInfo = authClient.getOrder(ethOrder['details']['order_id'])
ltcOrderInfo = authClient.getOrder(ltcOrder['details']['order_id'])
# new___Order true will get the next ___ order at the end of the while loop
newBtcOrder = False
newEthOrder = False
newLtcOrder = False

# Create lists to hold buy and sale events [#, price per coin, net cost, datetime, order #] on coinbase
cbBtcBuys = coinbaseClient.get_buys(cbAcntBtc['id'])
cbEthBuys = coinbaseClient.get_buys(cbAcntEth['id'])
cbLtcBuys = coinbaseClient.get_buys(cbAcntLtc['id'])
btcBought = []
for i in xrange(len(cbBtcBuys.data)):
    b = cbBtcBuys.data[-(i+1)]
    if b['transaction'] is not None:
        btcBought.append([float(b['amount'].amount), float(b['total'].amount)/float(b['amount'].amount),
                          float(b['total'].amount), dateutil.parser.parse(b['created_at']), b['id']])
# Add the 10 free coinbase dollars referral
cbBtcTrans = coinbaseClient.get_transactions(cbAcntBtc['id'])
for bTrans in cbBtcTrans.data:
    if "description" in bTrans and bTrans["description"] is not None and "Congrats!" in bTrans["description"]:
        btcBought.append([float(bTrans["amount"].amount), 0, 0, dateutil.parser.parse(bTrans["created_at"]), "referral bonus"])

ethBought = []
for i in xrange(len(cbEthBuys.data)):
    b = cbEthBuys.data[-(i + 1)]
    if b['transaction'] is not None:
        ethBought.append([float(b['amount'].amount), float(b['total'].amount)/float(b['amount'].amount),
                          float(b['total'].amount), dateutil.parser.parse(b['created_at']), b['id']])
ltcBought = []
for i in xrange(len(cbLtcBuys.data)):
    b = cbLtcBuys.data[-(i + 1)]
    if b['transaction'] is not None:
        ltcBought.append([float(b['amount'].amount), float(b['total'].amount)/float(b['amount'].amount),
                          float(b['total'].amount), dateutil.parser.parse(b['created_at']), b['id']])

# Create lists to store the sell transactions
btcSold = []
ethSold = []
ltcSold = []
processedOrderIds = []

print('Parsing all GDAX transactions...')
while btcIndex >= 0 or ethIndex >= 0 or ltcIndex >= 0:
    # see which order has the earliest time
    btcTime = dateutil.parser.parse(btcOrderInfo['done_at'])
    ethTime = dateutil.parser.parse(ethOrderInfo['done_at'])
    ltcTime = dateutil.parser.parse(ltcOrderInfo['done_at'])
    if btcIndex == -1:
        btcTime = datetime.datetime.now(tz=pytz.utc)
    if ethIndex == -1:
        ethTime = datetime.datetime.now(tz=pytz.utc)
    if ltcIndex == -1:
        ltcTime = datetime.datetime.now(tz=pytz.utc)
    timeList = [btcTime, ethTime, ltcTime]
    earliestIndex = timeList.index(min(timeList))
    if earliestIndex == 0:
        # Bitcoin transaction is the earliest, add to the order id's
        processedOrderIds.append(btcOrderInfo['id'])

        # See what the market is
        if btcOrderInfo['product_id'] == 'ETH-BTC':
            # Get the market prices at the time
            startTime = (dateutil.parser.parse(btcOrderInfo['done_at']) - datetime.timedelta(minutes=0.5)).strftime(
                "%Y-%m-%dT%H:%M:%S")
            endTime = (dateutil.parser.parse(btcOrderInfo['done_at']) + datetime.timedelta(minutes=0.5)).strftime(
                "%Y-%m-%dT%H:%M:%S")
            histRateBtc = []
            while type(histRateBtc) is not list or len(histRateBtc) == 0:
                if type(histRateBtc) is not list and len(histRateBtc) > 0:
                    time.sleep(20)
                histRateBtc = publicClient.getProductHistoricRates(product='BTC-USD', start=startTime,
                                                                   end=endTime, granularity='1')
            orderPriceBtc = histRateBtc[0][3]
            numBtc = float(btcOrderInfo['filled_size']) * float(btcOrderInfo['price'])
            numEth = float(btcOrderInfo['filled_size'])
            orderPriceEth = orderPriceBtc * numBtc / numEth
            if btcOrderInfo['side'] == 'buy':
                # sell btc, buy eth
                btcSold.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                btcOrder['details']['order_id']])
                ethBought.append([numEth, orderPriceEth, orderPriceEth*numEth, btcTime,
                                  btcOrder['details']['order_id']])
            elif btcOrderInfo['side'] == 'sell':
                # buy btc, sell eth
                btcBought.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                  btcOrder['details']['order_id']])
                ethSold.append([numEth, orderPriceEth, orderPriceEth*numEth, btcTime,
                                btcOrder['details']['order_id']])
            else:
                print 'FOUND A WEIRD ORDER!!! \n Order ID: %s \n btcGroup: %d, btcIndex: %d' % (btcOrderInfo['id'],
                                                                                                btcGroup, btcIndex)
###################### END ETH-BTC START BTC-USD ##############################
        elif btcOrderInfo['product_id'] == 'BTC-USD':
            numBtc = float(btcOrderInfo['filled_size'])
            orderPriceBtc = float(btcOrderInfo['price'])
            # see if it's a buy or sell
            if btcOrderInfo['side'] == 'sell':
                # sell bitcoin
                btcSold.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                btcOrder['details']['order_id']])
            if btcOrderInfo['side'] == 'buy':
                # buy bitcoin
                btcBought.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                  btcOrder['details']['order_id']])
###################### END BTC-USD START LTC-BTC ##############################
        elif btcOrderInfo['product_id'] == 'LTC-BTC':
            # Get the market prices at the time
            startTime = (dateutil.parser.parse(btcOrderInfo['done_at']) - datetime.timedelta(minutes=0.5)).strftime(
                "%Y-%m-%dT%H:%M:%S")
            endTime = (dateutil.parser.parse(btcOrderInfo['done_at']) + datetime.timedelta(minutes=0.5)).strftime(
                "%Y-%m-%dT%H:%M:%S")
            histRateBtc = []
            while type(histRateBtc) is not list or len(histRateBtc) == 0:
                if type(histRateBtc) is not list and len(histRateBtc) > 0:
                    time.sleep(20)
                histRateBtc = publicClient.getProductHistoricRates(product='BTC-USD', start=startTime,
                                                                   end=endTime, granularity='1')
            orderPriceBtc = histRateBtc[0][3]
            numBtc = float(btcOrderInfo['filled_size']) * float(btcOrderInfo['price'])
            numLtc = float(btcOrderInfo['filled_size'])
            orderPriceLtc = orderPriceBtc * numBtc / numLtc
            if btcOrderInfo['side'] == 'buy':
                # sell btc, buy ltc
                btcSold.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                btcOrder['details']['order_id']])
                ltcBought.append([numLtc, orderPriceLtc, orderPriceLtc*numLtc, btcTime,
                                  btcOrder['details']['order_id']])
            elif btcOrderInfo['side'] == 'sell':
                # buy btc, sell ltc
                btcBought.append([numBtc, orderPriceBtc, orderPriceBtc*numBtc, btcTime,
                                  btcOrder['details']['order_id']])
                ltcSold.append([numLtc, orderPriceLtc, orderPriceEth*numLtc, btcTime,
                                btcOrder['details']['order_id']])
            else:
                print 'FOUND A WEIRD ORDER!!! \n Order ID: %s \n btcGroup: %d, btcIndex: %d' % (btcOrderInfo['id'],
                                                                                                btcGroup, btcIndex)
        else:
            print 'UNKNOWN PRODUCT TYPE!!! \n Order ID: %s \n btcGroup: %d, btcIndex: %d' % (btcOrderInfo['id'],
                                                                                             btcGroup, btcIndex)

    elif earliestIndex == 1:
        # Ethereum transaction is the earliest, add to the order id's
        processedOrderIds.append(ethOrderInfo['id'])

        if ethOrderInfo['product_id'] == 'ETH-USD':
            if ethOrderInfo['done_reason'] != 'filled':
                print 'FOUND AN UNFILLED ORDER!!! \n Order ID: %s \n ethGroup: %d, ethIndex: %d' % (ethOrderInfo['id'],
                                                                                                    ethGroup, ethIndex)
            numEth = float(ethOrderInfo['filled_size'])
            if ethOrderInfo['type'] == 'market':
                orderPriceEth = (float(ethOrderInfo['fill_fees'])+float(ethOrderInfo['executed_value']))/numEth
            else:
                orderPriceEth = float(ethOrderInfo['price'])
            # see if it's a buy or sell
            if ethOrderInfo['side'] == 'sell':
                # sell etheruem
                ethSold.append([numEth, orderPriceEth, orderPriceEth*numEth, ethTime,
                                ethOrder['details']['order_id']])
            if ethOrderInfo['side'] == 'buy':
                # buy ethereum
                ethBought.append([numEth, orderPriceEth, orderPriceEth*numEth, ethTime,
                                  ethOrder['details']['order_id']])
        else:
            print 'UNKNOWN PRODUCT TYPE!!! \n Order ID: %s \n ethGroup: %d, ethIndex: %d' % (ethOrderInfo['id'],
                                                                                             ethGroup, ethIndex)
    elif earliestIndex == 2:
        # Litecoin transaction is the earliest, add to the order id's
        processedOrderIds.append(ltcOrderInfo['id'])

        if ltcOrderInfo['product_id'] == 'LTC-USD':
            if ltcOrderInfo['done_reason'] != 'filled':
                print 'FOUND AN UNFILLED ORDER!!! \n Order ID: %s \n ltcGroup: %d, ltcIndex: %d' % (ltcOrderInfo['id'],
                                                                                                    ltcGroup, ltcIndex)
            numLtc = float(ltcOrderInfo['filled_size'])
            if ltcOrderInfo['type'] == 'market':
                orderPriceLtc = (float(ltcOrderInfo['fill_fees'])+float(ltcOrderInfo['executed_value']))/numLtc
            else:
                orderPriceLtc = float(ltcOrderInfo['price'])
            # see if it's a buy or sell
            if ltcOrderInfo['side'] == 'sell':
                # sell litecoin
                ltcSold.append([numLtc, orderPriceLtc, orderPriceLtc*numLtc, ltcTime,
                                ltcOrder['details']['order_id']])
            if ltcOrderInfo['side'] == 'buy':
                # buy liteocin
                # First chcek to see if the coinbase transaction should be added
                # if addLtcOrder and ltcTime > ltcTransactionToAdd[3]:
                #     ltcBought.append(ltcTransactionToAdd)
                #     addLtcOrder = False
                ltcBought.append([numLtc, orderPriceLtc, orderPriceLtc*numLtc, ltcTime,
                                  ltcOrder['details']['order_id']])
        else:
            print 'UNKNOWN PRODUCT TYPE!!! \n Order ID: %s \n ltcGroup: %d, ltcIndex: %d' % (ltcOrderInfo['id'],
                                                                                             ltcGroup, ltcIndex)
    else:
        print('Error with earliest index!  This really should not happen!')

    # Decrement the btc, eth, and ltc ids if necessary
    while 'order_id' not in btcOrder['details'] or btcOrder['details']['order_id'] in processedOrderIds:
        [btcIndex, btcGroup] = decrementIndex(btcIndex, btcGroup, btcHistory)
        if btcIndex >= 0:
            btcOrder = btcHistory[btcGroup][btcIndex]
            newBtcOrder = True
        else:
            print("End of bitcoin orders!")
            newBtcOrder = False
            break
    while 'order_id' not in ethOrder['details'] or ethOrder['details']['order_id'] in processedOrderIds:
        [ethIndex, ethGroup] = decrementIndex(ethIndex, ethGroup, ethHistory)
        if ethIndex >= 0:
            ethOrder = ethHistory[ethGroup][ethIndex]
            newEthOrder = True
        else:
            print("End of ethereum orders!")
            newEthOrder = False
            break
    while 'order_id' not in ltcOrder['details'] or ltcOrder['details']['order_id'] in processedOrderIds:
        [ltcIndex, ltcGroup] = decrementIndex(ltcIndex, ltcGroup, ltcHistory)
        if ltcIndex >= 0:
            ltcOrder = ltcHistory[ltcGroup][ltcIndex]
            newLtcOrder = True
        else:
            print("End of litecoin orders!")
            newLtcOrder = False
            break

    while newBtcOrder:
        try:
            btcOrderInfo = authClient.getOrder(btcOrder['details']['order_id'])
            newBtcOrder = False
        except Exception as inst:
            print ('Error getting bitcoin order.  Will sleep for 20 seconds.')
            print type(inst)
            print inst.args
            print inst
            time.sleep(20)
    while newEthOrder:
        try:
            ethOrderInfo = authClient.getOrder(ethOrder['details']['order_id'])
            newEthOrder = False
        except Exception as inst:
            print ('Error getting ethereum order.  Will sleep for 20 seconds.')
            print type(inst)
            print inst.args
            print inst
            time.sleep(20)
    if newLtcOrder:
        try:
            ltcOrderInfo = authClient.getOrder(ltcOrder['details']['order_id'])
            newLtcOrder = False
        except Exception as inst:
            print ('Error getting litecoin order.  Will sleep for 20 seconds.')
            print type(inst)
            print inst.args
            print inst
            time.sleep(20)
print('Done parsing GDAX orders!')

# sort the buys and sell orders by datetime so we can do FIFO
datetimesBtc = []
datetimesEth = []
datetimesLtc = []
for b in btcBought:
    datetimesBtc.append(b[3])
for b in ethBought:
    datetimesEth.append(b[3])
for b in ltcBought:
    datetimesLtc.append(b[3])

btcSorted = [i[0] for i in sorted(enumerate(datetimesBtc), key=lambda x:x[1])]
ethSorted = [i[0] for i in sorted(enumerate(datetimesEth), key=lambda x:x[1])]
ltcSorted = [i[0] for i in sorted(enumerate(datetimesLtc), key=lambda x:x[1])]

btcBoughtSorted = []
ethBoughtSorted = []
ltcBoughtSorted = []

for i in btcSorted:
    btcBoughtSorted.append(btcBought[i])
for i in ethSorted:
    ethBoughtSorted.append(ethBought[i])
for i in ltcSorted:
    ltcBoughtSorted.append(ltcBought[i])

btcBoughtNet = np.sum([i[0] for i in btcBought]) - np.sum([i[0] for i in btcSold])
ethBoughtNet = np.sum([i[0] for i in ethBought]) - np.sum([i[0] for i in ethSold])
ltcBoughtNet = np.sum([i[0] for i in ltcBought]) - np.sum([i[0] for i in ltcSold])

# #### DO ANALYSIS ON THE BOUGHT AND SOLD LISTS #######
# list of [bought date, sell date, net $ sold, net $ cost, net $ gain, # coins sold]
def FIFO(boughtOrig, soldOrig, name):
    # copy the lists so we don't mess with them
    bought = copy.deepcopy(boughtOrig)
    sold = copy.deepcopy(soldOrig)

    fifoSales = []

    # go through every sold transaction and find the associated buy
    for s in sold:
        sellSize = s[0]
        # get the earliest buy transaction possible
        buySize = bought[0][0]
        # see if the sell order was larger than the oldest buy
        while sellSize > buySize:
            sellSize -= buySize
            fifoSales.append(["%1.5f " % buySize + name, bought[0][3].strftime('%m/%d/%Y'), s[3].strftime('%m/%d/%Y'),
                              s[1]*buySize, bought[0][2], s[1]*buySize-bought[0][2], buySize])
            bought.pop(0)
            s[0] -= buySize
            s[2] = s[2] - buySize*s[1]
            buySize = bought[0][0]
        # the sell order is not larger than the oldest buy, see if it is equal
        if sellSize == buySize:
            fifoSales.append(["%1.5f " % sellSize + name, bought[0][3].strftime('%m/%d/%Y'), s[3].strftime('%m/%d/%Y'),
                              s[2], bought[0][2], s[2]-bought[0][2], sellSize])
            bought.pop(0)
        elif sellSize > 0:
            # the sell order is smaller than the oldest buy
            bigBuy = bought[0]
            leftoverBuy = [bigBuy[0] - s[0], bigBuy[1], (bigBuy[0] - s[0])*bigBuy[1], bigBuy[3], bigBuy[4]]
            fifoSales.append(["%1.5f " % sellSize + name, bought[0][3].strftime('%m/%d/%Y'), s[3].strftime('%m/%d/%Y'),
                              s[2], bigBuy[2]-leftoverBuy[2], s[2]-(bigBuy[2]-leftoverBuy[2]), sellSize])
            bought[0] = leftoverBuy
    return fifoSales


def makePDF(fifoResult, fname, person, social):
    # Write to the PDF
    from fdfgen import forge_fdf

    counter = 0
    fileCounter = 0
    fields = [('topmostSubform[0].Page1[0].f1_1[0]', person),
              ('topmostSubform[0].Page1[0].f1_2[0]', social)]
    fnums = [3+i*8 for i in range(14)]
    lastRow1 = 0
    lastRow2 = 0
    lastRow3 = 0
    lastRow4 = 0
    # loop through all FIFO sales
    for sale in fifoResult:
        counter += 1
        # append to the form
        row = counter
        fnum = fnums[row-1]
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum), sale[0]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+1), sale[1]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+2), sale[2]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+3), "%1.2f" % sale[3]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+4), "%1.2f" % sale[4]))
        if (sale[3]-sale[4]) < 0:
            fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum + 7),
                           "(%1.2f)" % (sale[4] - sale[3])))
        else:
            fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+7), "%1.2f" % (sale[3]-sale[4])))

        lastRow1 += float("%1.2f" % sale[3])
        lastRow2 += float("%1.2f" % sale[4])
        lastRow3 += 0
        lastRow4 += float("%1.2f" % (sale[3]-sale[4]))

        if row == 14 or sale == fifoResult[-1]:
            fields.append(("topmostSubform[0].Page1[0].f1_115[0]", "%1.2f" % lastRow1))
            fields.append(("topmostSubform[0].Page1[0].f1_116[0]", "%1.2f" % lastRow2))
            if lastRow4 < 0:
                fields.append(("topmostSubform[0].Page1[0].f1_118[0]", "(%1.2f)" % abs(lastRow4)))
            else:
                fields.append(("topmostSubform[0].Page1[0].f1_118[0]", "%1.2f" % lastRow4))
            fields.append(("topmostSubform[0].Page1[0].c1_1[2]", 3))
            # save the file and reset the counter
            fdf = forge_fdf("", fields, [], [], [])
            fdf_file = open("FDFs\\" + fname + "_%03d.fdf" % fileCounter, "w")
            fdf_file.write(fdf)
            fdf_file.close()
            # call PDFTK to make the PDF
            os.system("pdftk f8949.pdf fill_form FDFs\\" + fname + "_%03d.fdf" % fileCounter + " output PDFs\\" +
                      fname + "_%03d.pdf" % fileCounter)
            # delete the FDF
            os.system("del FDFs\\" + fname + "_%03d.fdf" % fileCounter)
            counter = 0
            fileCounter += 1
            fields = []
            lastRow1 = 0
            lastRow2 = 0
            lastRow3 = 0
            lastRow4 = 0


# Make the pdfs
if not os.path.exists("FDFs"):
    os.makedirs("FDFs")
if not os.path.exists("PDFs"):
    os.makedirs("PDFs")

bFIFO = FIFO(btcBoughtSorted, btcSold, "bitcoin")
eFIFO = FIFO(ethBoughtSorted, ethSold, "ethereum")
lFIFO = FIFO(ltcBoughtSorted, ltcSold, "litecoin")

print('Filling out the 8949 forms...')
makePDF(bFIFO, "bitcoin", myname, ss)
makePDF(eFIFO, "ethereum", myname, ss)
makePDF(lFIFO, "litecoin", myname, ss)
# delete the FDFs directory
os.system("rmdir FDFs")
print('Done!')