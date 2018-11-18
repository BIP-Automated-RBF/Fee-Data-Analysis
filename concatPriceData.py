import csv
import time

t0 = time.time()

# Using data from https://www.kaggle.com/mczielinski/bitcoin-historical-data
with open('bitcoin-historical-data/coinbaseUSD_1-min_data_2014-12-01_to_2018-11-11.csv') as originalSet:
    with open('bitcoin-historical-data/coinbaseUSD_10-min_data_2016-12-31_to_2018-11-11.csv', mode='w') as newSet:
        reader = csv.reader(originalSet, delimiter=',')
        writer = csv.writer(newSet)

        # The time just before the first block we want to write from (446000)
        initialTime = 1483206600
        # Write the header
        writer.writerow(next(reader))

        # Go through every 1min candle row and copy every 10th row if it's after initialTime
        for i, row in enumerate(reader):
            if ((int(row[0]) % 600) == 0 and int(row[0]) >= initialTime):
                writer.writerow(row)

print('Finished, time taken = ', (time.time() - t0))