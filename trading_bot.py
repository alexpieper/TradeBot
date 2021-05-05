import pandas as pd
import numpy as np
import time
import datetime
import os

import logging

from binance.client import Client
from binance.enums import *

import utils
import config


log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

data_folder = "data"

    

def start_trading_bot(client, trade_pairs, kline_size, window_short, window_long):
    
    #### Initialization ####
    DF_dict = {}
    positions = {}
    for symbol in trade_pairs:
        # pull initial dataframes
        utils.delete_data(symbol, kline_size)
        DF_dict[symbol] = utils.retrieve_data(client, symbol, kline_size, save = True, start = "2021-04-13")

        # get information about current investments:
        bal = utils.get_currency_balance(client, symbol)
        if (float(bal) * float(DF_dict[symbol]["close"].iloc[-1])) > 3:
            positions[symbol] = True
        else:
            positions[symbol] = False
    print(positions)
        
    
    #### Actual bot ####
    while True:
        log.info(f'########################### Next Iteration: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ########################### ')
        start = time.time()
        for symbol in trade_pairs:
            log.info(f"########################### {symbol} ###########################")
            # update data, try catch the potential api resetting
            try:
                DF_dict[symbol] = utils.update_data(client, symbol, kline_size, save = True)
            except Exception as e:
                print(e)
                log.info(f"Data pull error on Binance side, waiting 15 minutes to reconnect")
                break


            # calculating rolling_windows and z-score
            DF_dict[symbol]         = utils.make_rolling_and_score(DF_dict[symbol], windows_short[symbol], windows_long[symbol])
            print(DF_dict[symbol].tail(5))
            current_opportunity     = DF_dict[symbol]["score"].iloc[-1]
            log.info(f"Z-Score of {symbol}:            {current_opportunity}")

            # getting account information like balance etc.
            try:
                bal = utils.get_currency_balance(client, symbol)
            except Exception as e:
                print(e)
                log.info(f"Data pull error on Binance side, waiting 15 minutes to reconnect")
                break

            log.info(f'current balance of {symbol.split("EUR")[0]}:       {bal}')
            
            # check opportunities and potentially issue an order
            if current_opportunity > 0:
                if positions[symbol]:
                    pass
                else:
                    # Actual buy function, handle with care!
                    order = client.create_order(symbol = symbol,
                                                side = SIDE_BUY,
                                                type = ORDER_TYPE_MARKET,
                                                quoteOrderQty = 300)
                    print(order)
                    positions[symbol] = True

                    
                    log.info(f'                                         market BUY order placed for {symbol} !!!')
                    
            else:
                if positions[symbol]:
                    # Actual sell function, handle with care!
                    decimal_place = 15
                    while decimal_place > -1:
                        try:
                            order = client.create_order(symbol = symbol,
                                                    side = SIDE_SELL,
                                                    type = ORDER_TYPE_MARKET,
                                                    quantity = quantity)
                            break
                        except:
                            decimal_place -= 1
                            quantity = np.round(float(client.get_asset_balance(asset=symbol.split("EUR")[0])["free"]), decimal_place)
                    
                    print(order)
                    positions[symbol] = False

                    log.info(f'                                         market SELL order placed for {symbol} !!!')

                else:
                    pass
        end = time.time()
        # sleep for exactly 15 minutes since start
        time.sleep(60 * 15 - (end - start) - 1/24)
    

if __name__ == "__main__":
    client = Client(config.api_key, config.secret_key)
    trade_pairs = ["BTCEUR", "ETHEUR", "DOGEEUR", "XRPEUR"]
    kline_size = "15m"

    # windows dependant on symbol, results are base on backtesting
    # adjustments needed for different trade pairs and kline_sizes
    windows_short = {"BTCEUR": 20, 
                     "ETHEUR": 46, 
                     "DOGEEUR": 50,
                     "XRPEUR": 24
                     }
    windows_long = {"BTCEUR": 240, 
                     "ETHEUR": 330, 
                     "DOGEEUR": 100,
                     "XRPEUR": 400
                     }

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    start_trading_bot(client, trade_pairs, kline_size, windows_short, windows_long)


