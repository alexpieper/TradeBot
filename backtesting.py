import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

from binance.client import Client

import utils
import config

result_folder = "backtest_evaluations"

def backtesting_single(pair, kline_size, data, windows_short, windows_long, trading_cost = False):
    data.index = pd.DatetimeIndex(data.index)

    data["rolling_s"] = data["close"].rolling(windows_short).mean()
    data["rolling_l"] = data["close"].rolling(windows_long).mean()
        
    data = data[["close", "rolling_s", "rolling_l"]]
    data["score"] = (data["rolling_s"] - data["rolling_l"]) / data["close"].rolling(windows_short).std()
    data = data.dropna(axis = 0)

    data["Invest_ratio"] = data["score"].apply(lambda x: 1 if x > 0.0 else 0)
    data['ret'] = np.log(1.0 + data['close'].astype(float).pct_change().fillna(0.0)).shift(-1)
    data['My_strategy'] = np.exp((data['ret'] * data['Invest_ratio']).cumsum()) - 1.0
    data['Benchmark'] = np.exp((data['ret']).cumsum()) - 1.0
    
    if trading_cost:
        data["Trade"] = data["Invest_ratio"].diff() != 0
        for index, row in data.iterrows():
            if row["Trade"] == True:
                data.loc[data.index > index, 'My_strategy'] = data.loc[data.index > index, 'My_strategy'] - 0.001


    # data['Difference'] = np.exp((data['ret'] * (data['Invest_ratio'] - 1.0)).cumsum()) - 1.0
    data['Difference'] = np.exp(np.log(1 + data["My_strategy"]) - np.log(1 + data['Benchmark'])) + 1

    data.to_csv(os.path.join(result_folder, kline_size, pair + "_" + str(kline_size) + "_" + str(windows_short) + "_" + str(windows_long) + ".csv"))
    utils.create_plot(data, pair, kline_size, windows_short, windows_long)

def perform_backtesting(pair, kline_size, data, windows_short, windows_long):
    data.index = pd.DatetimeIndex(data.index)
    outperformance_map = pd.DataFrame(index = windows_short, columns = windows_long)
    data_orig = data.copy()
    for win_s in windows_short:
        for win_l in windows_long:
            if win_s > win_l:
                continue
            data = data_orig.copy()
            data["rolling_s"] = data["close"].rolling(win_s).mean()
            data["rolling_l"] = data["close"].rolling(win_l).mean()
                
            data = data[["close", "rolling_s", "rolling_l"]]
            data["score"] = (data["rolling_s"] - data["rolling_l"]) / data["close"].rolling(win_s).std()
            data = data.dropna(axis = 0)

            data["Invest_ratio"] = data["score"].apply(lambda x: 1 if x > 0.0 else 0)
            data['ret'] = np.log(1.0 + data['close'].astype(float).pct_change().fillna(0.0)).shift(-1)
            data['My_strategy'] = np.exp((data['ret'] * data['Invest_ratio']).cumsum()) - 1.0
            data['Benchmark'] = np.exp((data['ret']).cumsum()) - 1.0
            data['Difference'] = np.exp((data['ret'] * (data['Invest_ratio'] - 1.0)).cumsum()) - 1.0
            # print(data)
            outperformance_map.loc[win_s,win_l] = data['Difference'].iloc[-2]

    outperformance_map = outperformance_map.fillna(outperformance_map.min().min())
    fig, ax = plt.subplots(figsize=(33,18))
    sns.heatmap(outperformance_map, annot=True)
    fig.tight_layout()
    plt.savefig(os.path.join(result_folder, kline_size, pair + "_" + kline_size + "_results.png"))



if __name__ == "__main__":
    client = Client(config.api_key, config.secret_key)
    trade_pairs = ["BTCEUR", "ETHEUR", "DOGEEUR", "XRPEUR", "ADAEUR"]
    # trade_pairs = ["ADAEUR"]
    kline_size = "1m"

    windows_short = np.linspace(200,2000,50).astype(int)
    windows_long = np.linspace(400,4000,50).astype(int)

    if not os.path.exists(os.path.join(result_folder, kline_size)):
        os.makedirs(os.path.join(result_folder, kline_size))

    for pair in trade_pairs:
        data = utils.retrieve_data(client, pair, kline_size, start = "2020-01-01")
        perform_backtesting(pair, kline_size, data, windows_short, windows_long)
    

    windows_short = {"15m":
                        {"BTCEUR": 20, 
                         "ETHEUR": 46, 
                         "DOGEEUR": 50,
                         "ADAEUR": 128,
                         "XRPEUR": 24
                         },
                    "5m":
                        {"BTCEUR": 152, 
                         "ETHEUR": 132, 
                         "DOGEEUR": 136,
                         "ADAEUR": 128,
                         "XRPEUR": 164
                         },
                    "1m":
                        {"BTCEUR": 750, 
                         "ETHEUR": 640, 
                         "DOGEEUR": 640,
                         "ADAEUR": 640,
                         "XRPEUR": 800
                         }
                    }

    windows_long = {"15m":
                        {"BTCEUR": 240, 
                         "ETHEUR": 330, 
                         "DOGEEUR": 100,
                         "ADAEUR": 128,
                         "XRPEUR": 400
                         },
                    "5m":
                        {"BTCEUR": 203, 
                         "ETHEUR": 195, 
                         "DOGEEUR": 297,
                         "ADAEUR": 172,
                         "XRPEUR": 295
                         },
                    "1m":
                        {"BTCEUR": 1000, 
                         "ETHEUR": 1000, 
                         "DOGEEUR": 1500,
                         "ADAEUR": 900,
                         "XRPEUR": 1500
                         }
                    }
    

    for pair in trade_pairs:
        # data = utils.retrieve_data(client, pair, kline_size, start = "2020-01-01")
        data = utils.load_data(client, pair, kline_size)
        print(data)
        backtesting_single(pair, kline_size, data, windows_short[kline_size][pair], windows_long[kline_size][pair], trading_cost = True)

    