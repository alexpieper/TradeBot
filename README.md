# Cryptocurrency Trading Bot using the Binance API
This trading bot uses the API from he cryptocurrency exchange Binance (https://www.binance.com), to check for buying/selling oppotunities and execute trades automatically with a 15 minute interval.

As Indicator, a very Basic Simple Moving Average Crossover (SMAC) is considered. In short: When the short-term Moving average is higher then the long term moving average: BUY. Otherwise SELL. 

I am not an investment Instructor, nor qualified as such. Trading with Crypto currencies is very risky.
Therefore this is not a Trading recommendation.
Adaption at own risk.

## Requirements:
+ Binance Account
+ API keys (can be created via binance Website)
+ some standard python packages like datetime, pandas
+ python package: binance (pip install python-binance)


## Scripts:
+ utils.py:
    contains helper functions like data retrieval and 
+ config.py: 
    contains the API-key and secret-key as strings
+ backtesting.py:
    performs backtesting with the data from binance and creates heatmaps/performance-graphs
    + Output:
        + perform_backtesting(): Heatmap per trade pair in backtest_evaluations, compairing different rolling windows for the SMAC-Indicator
        + backtesting_single(): Plot with Indicator, Performance and Outperformance, w.r.t. the underlying crypto.
+ trading_bot.py:
    Is the actual trading bot, that can execute buy or sell orders. It is running constantly and checks buying oppotunities every 15 minutes 
    + Parameters:
        + kline_size = "15m", (str), determines the interval in which data should be pulled and opportunities should be checked and executed. (see binance api docs for more).
        + trade_pairs = ["BTCEUR", "ETHEUR", "DOGEEUR", "XRPEUR"], (list), determines the trade pairs to consider. 
        + windows_short/long = {}, (dictionary), determines the SMA rolling window per trade pair.
    + Output:
        + Executes trades on your binance account
        + write an order_book.csv, containing all trades executed. needs empty initialized file at beginning.

## Future Ideas
+ send messages, when trades are executed, containing relevant information.
