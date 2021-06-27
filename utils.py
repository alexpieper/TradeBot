import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import os
from datetime import timedelta, datetime
from dateutil import parser
import logging
import json


import config

log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

binsizes = {"1m": 1,
            "3m": 3, 
            "5m": 5, 
            "15m": 15, 
            "30m": 30, 
            "1h": 60, 
            "2h": 120, 
            "4h": 240, 
            "6h": 360, 
            "8h": 480, 
            "12h": 720, 
            "1d": 1440,
            "3d": 1440*3,
            "1w": 1440*3*7,
            "1M": 1440*3*7*4,
            }
data_folder = "data"

##########################################
############ Account Handling ############
##########################################

def check_account_infos(client):

    info = client.get_account()
    log.info('logged in')


def get_currency_balance(client, symbol):
    bal = client.get_account()["balances"]
    base_currency = symbol.split("EUR")[0]
    try:
        return bal[[bal[i]["asset"] == base_currency for i in range(len(bal))].index(True)]["free"]
    except:
        return 0





#######################################
############ Data handling ############
#######################################

def minutes_of_new_data(client, symbol, kline_size, data, start = '2020-01-01'):
    # code derived from: https://medium.com/swlh/retrieving-full-historical-data-for-every-cryptocurrency-on-binance-bitmex-using-the-python-apis-27b47fd8137f
    if len(data) > 0:  
        old = parser.parse(data.index.tolist()[-1])
    else: 
        old = datetime.strptime(start, '%Y-%m-%d')
    new = pd.to_datetime(client.get_klines(symbol=symbol, interval=kline_size)[-1][0], unit='ms')
    return old, new



def retrieve_data(client, symbol, kline_size, save = False, start = '2020-01-01'):
    # code derived from: https://medium.com/swlh/retrieving-full-historical-data-for-every-cryptocurrency-on-binance-bitmex-using-the-python-apis-27b47fd8137f
    filename                    = f'{symbol}-{kline_size}-data.csv'
    data_df                     = pd.DataFrame()
    oldest_point, newest_point  = minutes_of_new_data(client, symbol, kline_size, data_df, start = start)
    delta_min                   = (newest_point - oldest_point).total_seconds()/60
    available_data              = math.ceil(delta_min/binsizes[kline_size])
    
    log.info(f'Downloading {delta_min} minutes of new data available for {symbol}, i.e. {available_data} instances of {kline_size} data.')
    klines                      = client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"), newest_point.strftime("%d %b %Y %H:%M:%S"))
    data                        = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    data                        = data[['timestamp', 'close', 'volume']]
    data['timestamp']           = pd.to_datetime(data['timestamp'], unit='ms')
    data                        = data.set_index("timestamp")
    data.index                  = pd.DatetimeIndex(data.index)
    data.to_csv(os.path.join(data_folder,filename))
    return data



def update_data(client, symbol, kline_size, save = False):
    filename                    = f'{symbol}-{kline_size}-data.csv'
    data_df                     = pd.read_csv(os.path.join(data_folder,filename), index_col = 0)
    oldest_point, newest_point  = minutes_of_new_data(client, symbol, kline_size, data_df)
    oldest_point                = oldest_point + timedelta(minutes = binsizes[kline_size])

    klines                      = client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"), newest_point.strftime("%d %b %Y %H:%M:%S"))
    data                        = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    data                        = data[['timestamp', 'close', 'volume']]
    data['timestamp']           = pd.to_datetime(data['timestamp'], unit='ms')
    data                        = data.set_index("timestamp")
    data.index                  = pd.DatetimeIndex(data.index)

    temp_df = pd.DataFrame(data)
    data_df = data_df.append(temp_df)
    # truncate to save speed and storage:
    data_df = data_df.iloc[-2000:,:]
    if save: 
        data_df.to_csv(os.path.join(data_folder,filename))
    return data_df




def load_data(client, symbol, kline_size):
    filename = f'{symbol}-{kline_size}-data.csv'
    if os.path.isfile(os.path.join(data_folder,filename)): 
        data_df = pd.read_csv(os.path.join(data_folder,filename), index_col = 0)
    else: 
        log.error("DF is not available")
        return
    return data_df

def delete_data(symbol, kline_size):
    filename = f'{symbol}-{kline_size}-data.csv'
    if os.path.isfile(os.path.join(data_folder,filename)): 
        os.remove(os.path.join(data_folder,filename))
    else: 
        log.error("DF is not available")


def make_rolling_and_score(DF, window_short, window_long):
    DF["rolling_short"]     = DF["close"].rolling(window_short).mean()
    DF["rolling_long"]      = DF["close"].rolling(window_long).mean()
    DF["score"]             = (DF["rolling_short"] - DF["rolling_long"]) / DF["close"].rolling(window_long).std()
    return DF



##########################################
############ Graphic handling ############
##########################################

def create_plot(data, pair, kline_size, short, long):
    subTitles = ["Indicator", "Returns", "Outperformance"]


    fig, ax = plt.subplots(figsize=(15, 9),
                           nrows=3,
                           ncols=1,
                           sharex=True,
                           linewidth=2,
                           edgecolor="black",
                           gridspec_kw={"height_ratios": [1, 2, 2]})

    
    
    ax[0].plot(
        data.index,
        data["Invest_ratio"] * 100,
        color="black",
        linewidth=2,
    )
    ax[0].set_title(subTitles[0], fontdict={"fontsize": 18})
    ax[0].grid()
    ax[0].spines['right'].set_visible(False)
    ax[0].spines['top'].set_visible(False)

    ax[1].plot(data["My_strategy"].index,
               data["My_strategy"] * 100,
               color="tab:green",
               linewidth=2,
               label="My_strategy")
    ax[1].plot(data["Benchmark"].index,
               data["Benchmark"] * 100,
               color="tab:blue",
               linewidth=2,
               label="Benchmark")


    ax[1].set_title(subTitles[1], fontdict={"fontsize": 18})
    ax[1].grid()
    ax[1].legend(loc="upper left")
    ax[1].spines['right'].set_visible(False)
    ax[1].spines['top'].set_visible(False)

    ax[2].plot(
        data["Difference"].index.tolist(),
        data["Difference"] * 100,
        color="tab:green",
        linewidth=2,
    )
    ax[2].set_title(subTitles[2], fontdict={"fontsize": 18})
    ax[2].grid()
    ax[2].spines['right'].set_visible(False)
    ax[2].spines['top'].set_visible(False)

    fig.suptitle(pair, x=0.51, ha="right", fontsize=24)
    fig.tight_layout()
    plt.savefig(os.path.join("backtest_evaluations", kline_size, + pair + "_" + str(kline_size) + "_" + str(short) + "_" + str(long) + ".jpeg"))

if __name__ == "__main__":
    from binance.client import Client
    client = Client(config.api_key, config.secret_key)
    retrieve_data(client, "DOGEUSDT", "5m", save = True, start = "2021-01-01")