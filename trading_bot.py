import pandas as pd
import numpy as np
import time
import datetime
from datetime import timedelta
import os

import logging

from binance.client import Client
from binance.enums import *

import utils
import config


log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

data_folder = "data"

def trunc(values, decs=0):
    return np.trunc(values*10**decs)/(10**decs)
    

def start_trading_bot(client, trade_pairs, kline_size, windows_short, windows_long):
    
    #### Initialization ####
    DF_dict = {}
    positions = {}
    start_day = (datetime.datetime.now() - timedelta(days = 2)).strftime("%Y-%m-%d")
    for symbol in trade_pairs:
        # pull initial dataframes
        utils.delete_data(symbol, kline_size)
        DF_dict[symbol] = utils.retrieve_data(client, symbol, kline_size, save = True, start = start_day) 

        # get information about current investments:
        bal = utils.get_currency_balance(client, symbol)
        if (float(bal) * float(DF_dict[symbol]["close"].iloc[-1])) > 1:
            positions[symbol] = True
        else:
            positions[symbol] = False    
    
    #### Actual bot ####
    skip_next = False
    while int(datetime.datetime.now().strftime("%S")) != 54:
        time.sleep(1)
    while True:
        now = datetime.datetime.now()
        for symbol in trade_pairs:
            # update data, try catch the potential api resetting
            try:
                DF_dict[symbol] = utils.update_data(client, symbol, kline_size, save = True)
            except Exception as e:
                print(e)
                log.info(f"Data pull error on Binance side, waiting to reconnect")
                skip_next = True
                break

        for symbol in trade_pairs:
            if skip_next:
                skip_next = False
                break
            # calculating rolling_windows and z-score
            DF_dict[symbol]         = utils.make_rolling_and_score(DF_dict[symbol], windows_short[symbol], windows_long[symbol])
            current_opportunity     = float(DF_dict[symbol]["score"].iloc[-1])

            if int(now.strftime("%M")) in [30,0]:
                if symbol == trade_pairs[0]:
                    log.info(f'########################### Time: {now.strftime("%Y-%m-%d %H:%M:%S")} ########################### ')
                price = float(DF_dict[symbol]['close'].iloc[-1])
                log.info(f"Z-Score of {symbol}:\t\t{np.round(current_opportunity,4)}, price:\t\t{np.round(price,5)}")
                

            # getting account information like balance etc.
            try:
                bal = utils.get_currency_balance(client, symbol)
            except Exception as e:
                print(e)
                log.info(f"Data pull error on Binance side, waiting 15 minutes to reconnect")
                break

            
            # check opportunities and potentially issue an order
            if current_opportunity > 0:
                if positions[symbol]:
                    pass
                else:
                    # Actual buy function, handle with care!
                    try:
                        order = client.create_order(symbol = symbol,
                                                    side = SIDE_BUY,
                                                    type = ORDER_TYPE_MARKET,
                                                    quoteOrderQty = 250)
                    except:
                        try:
                            order = client.create_order(symbol = symbol,
                                                        side = SIDE_BUY,
                                                        type = ORDER_TYPE_MARKET,
                                                        quoteOrderQty = client.get_asset_balance(asset="EUR")["free"])
                        except:
                            log.info(f'Tried to buy {symbol}, but the balance is too low, to no trade can be executed')
                            continue
                    positions[symbol] = True
                    buy_price = np.round(float(order['fills'][0]['price']),5)
                    eur_amount = np.round(float(order['cummulativeQuoteQty']),2)
                    log.info(f'##################################################################### ')
                    log.info(f'########################### Buy Executed! ########################### ')
                    log.info(f'########################### Time: {now.strftime("%Y-%m-%d %H:%M:%S")} ############### ')
                    log.info(f'######## BUY order placed for {symbol} at {buy_price} for {eur_amount} EUR ######## ')
                    log.info(f'########################### Buy Executed! ########################### ')
                    log.info(f'##################################################################### ')
                    
            else:
                if positions[symbol]:
                    # Actual sell function, handle with care!
                    decimal_place = 15
                    quantity = trunc(float(client.get_asset_balance(asset=symbol.split("EUR")[0])["free"]), decimal_place)     
                    
                    #  because of the different magnitudes of the currencies (i.e. Doge = 0.3 EUR, BTC = 30000 EUR)
                    if symbol in ["ETHEUR", "BTCEUR"]:
                        min_dec_place = 2
                    else:
                        min_dec_place = -1
                    while decimal_place > min_dec_place:
                        try:
                            order = client.create_order(symbol = symbol,
                                                    side = SIDE_SELL,
                                                    type = ORDER_TYPE_MARKET,
                                                    quantity = quantity)
                            positions[symbol] = False
                            sell_price = np.round(float(order['fills'][0]['price']),5)
                            eur_amount = np.round(float(order['cummulativeQuoteQty']),2)
                            log.info(f'##################################################################### ')
                            log.info(f'########################### SELL Executed! ########################## ')
                            log.info(f'########################### Time: {now.strftime("%Y-%m-%d %H:%M:%S")} ############### ')
                            log.info(f'###### Sell order placed for {symbol} at {sell_price} for {eur_amount} EUR ######## ')
                            log.info(f'########################### SELL Executed! ########################## ')
                            log.info(f'##################################################################### ')
                            break
                        except:
                            decimal_place -= 1
                            # is should always round down, not up. therefore trunc() not np.round().
                            
                            quantity = trunc(float(client.get_asset_balance(asset=symbol.split("EUR")[0])["free"]), decimal_place)     

                else:
                    pass
        # start next iteration at exactly 50 second onto the minute
        second = int(datetime.datetime.now().strftime("%S"))
        if second >= 54:
            time.sleep(54 + 60 - second)
        else:
            time.sleep(54 - second)
    

if __name__ == "__main__":
    client = Client(config.api_key, config.secret_key)
    trade_pairs = ["BTCEUR", "ETHEUR", "DOGEEUR", "XRPEUR"]
    kline_size = "1m"

    # windows dependant on symbol, results are base on backtesting
    # adjustments needed for different trade pairs and kline_sizes
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
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)


    start_trading_bot(client, trade_pairs, kline_size, windows_short = windows_short[kline_size], windows_long = windows_long[kline_size])


