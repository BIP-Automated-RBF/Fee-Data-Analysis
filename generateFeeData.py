# Author: James Key
# This script parses all the txs since block startBlockHeight until latestBlockHeight into a csv file, then another
# script will do the actual data processing into another csv file - it would take too much memory to
# hold an array of all the tx fee data. A potential issue with this script is that it doesn't check the integrity of
# past data. This would be an issue if this parser stopped running while having written only part of a block to the
# file - if it does so at block N, the parser won't fill in the missing data for block N, but will instead move on
# to writing block N+1. A potential solution would be to, upon this parser starting and reading the latest block height
# written, check if the number of lines (the number of txs) written for the block height in question is equal to the
# number of txs that it should contain by quering the noe RPC. If it's not equal, then copy over all the 'good' block
# data to a new csv file without the 'bad' blocks, and fill in the missing data as you go. However, since the vast
# majority of the time it takes to write a block to CSV (~=30s) is looking up input data from the node RPC, and the
# data writing itself for each block should be far less than 1s, it would be easiest to just check the integrity of the
# dataset once parsing has finished so this only ever needs to be done once.

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import configparser
import csv
import os

t0 = time.time()

# Read from the parser's conf file and connect to the node's RPC
conf = configparser.ConfigParser()
conf.read("btcparser.conf")
nodeCredentials = conf["config"]["nodeCredentials"]
node = AuthServiceProxy(nodeCredentials)
# Block from the start of 2017 is 446000
# Block height to start parsing from
startBlockHeight = 525000
# The last block to be parsed since it's before the end of our price data time-wise. The last block WON'T be included
latestBlockHeight = 549500

priceDataFileName = "bitcoin-historical-data/coinbaseUSD_10-min_data_2016-12-31_to_2018-11-11.csv"
feeDataFileName = "bitcoin-historical-data/txFeeDataFromBlock{}To{}.csv".format(startBlockHeight, latestBlockHeight)

# Open priceData file
with open(priceDataFileName) as priceData:

    # Need to check if the feeData file exists so the header can be written if not
    if not os.path.isfile(feeDataFileName):
        with open(feeDataFileName, 'w') as feeData:
            feeDataWriter = csv.writer(feeData)
            feeDataWriter.writerow(["height", "time", "btcPrice", "txid", "txVSize", "btcSpent", "usdSpent", "feeInBtc",
                                    "feeInUSD", "btcPerVByte", "USDPerVByte"])
    # If it does exist, read the last block height that was written to it
    else:
        with open(feeDataFileName) as feeData:
            feeDataReader = csv.reader(feeData, delimiter=',')
            # Skip to the 2nd row where the price data actually starts
            next(feeDataReader)
            next(feeDataReader)
            for row in feeDataReader:
                if int(row[0]) >= startBlockHeight: startBlockHeight = int(row[0])+1

    # Start editing the data
    with open(feeDataFileName, 'a') as feeData:

        priceDataReader = csv.reader(priceData, delimiter=',')
        feeDataWriter = csv.writer(feeData)

        # Skip to the 2nd row where the price data actually starts
        row = next(priceDataReader)
        row = next(priceDataReader)

        # Iterate through blocks
        for height in range(startBlockHeight, latestBlockHeight):
            print('Height: ', height)
            # Get block data from the node
            block = node.getblock(node.getblockhash(height))
            # This will be a 2d list - a list where each element is a list of data for an individual tx
            txsData = []

            # Find the price data that was the latest before the block was mined
            while not (block['time'] >= (int(row[0])) and block['time'] <= int(row[0])+600):
                row = next(priceDataReader)
            btcPrice = float(row[7])

            # Iterate through every tx in a block. Don't want to include the coinbase tx when iterating through
            # each tx in a block
            for txid in block['tx'][1:]:
                totalIn = 0
                totalOut = 0

                # Get data of a tx
                tx = node.decoderawtransaction(node.getrawtransaction(txid), True)

                try:
                    # Need the total Bitcoins being used as inputs
                    for input in tx['vin']:
                        # Need to know which index of an output of this tx is being spent
                        index = input['vout']
                        # The node only refers to the txid of the output that's being spent in this input, so need to fetch
                        # that first
                        txo = node.decoderawtransaction(node.getrawtransaction(input['txid']), True)
                        # Need to get the actual output of this tx being spent to get the amount
                        totalIn += txo['vout'][index]['value']

                    # Need the total Bitcoins being spent as outputs
                    for output in tx['vout']:
                        totalOut += output['value']

                    totalIn = float(totalIn)
                    totalOut = float(totalOut)
                    feeBtc = totalIn - totalOut

                    # Get a list of tx data in this block so they can be sorted by the fee/vByte
                    txsData.append([height, block['time'], btcPrice, txid, tx['vsize'], totalOut, totalOut*btcPrice, feeBtc,
                                    feeBtc*btcPrice, feeBtc/tx['vsize'], feeBtc*btcPrice/(tx['vsize'])])
                except Exception as e:
                    print(e)
                    print(txid)
                    print(input)

            # Sort every tx in a block by the fee/vByte from smallest to largest
            sortedTxsData = sorted(txsData, key=lambda x: x[9])
            # Write the sorted data into the csv file
            for feeInfo in sortedTxsData:
                feeDataWriter.writerow(feeInfo)
            t1 = time.time()-t0
            print("Time elapsed: {} s        {} mins          {} hours          {} days".format(t1, t1/60, t1/3600, t1/86400))

