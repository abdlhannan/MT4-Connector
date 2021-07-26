from ZeroMQ_Connector import ZeroMQ_Connector
from Periodic_Timer_Thread import Periodic_Timer_Thread
import datetime
import pandas as pd
from pandas import DataFrame, to_datetime
from time import sleep
import sched
import time
import threading
import os
import json
import re
import MetaTrader5 as mt5
class AccountManagement(ZeroMQ_Connector):
    def __init__(self, PATH,
                strategy_name,
                server_offset,
                start_day_balance,
                dailyrisk=True,
                breakeven_SL=False,
                breakeven_perc=0.50,
                daily_limit=0.04,
                max_limit=0.09, risk_per_trade=0.01, lot_size=0.01):
        super().__init__()
        self.PENDING_ORDERS_DIR = './pending_orders_logs'
        self.PATH = PATH
        self.strategy_name = strategy_name
        self.dailyrisk = dailyrisk
        self.breakeven_SL = breakeven_SL
        self.breakeven_perc = breakeven_perc
        self.daily_limit = daily_limit
        self.max_limit = max_limit
        self.risk_per_trade = risk_per_trade
        self.lot_size = lot_size
        self.initial_balance = self.calculate_initial_deposit()
        self.threads_list = []
        self.halt_trading_completely = False
        self.halt_trading_daily = False
        self.server_offset = server_offset
        self.start_day_balance = start_day_balance
        self.scheduler_object = sched.scheduler(time.time, time.sleep)
        if os.path.isdir(self.PENDING_ORDERS_DIR) == False:
            os.makedirs(self.PENDING_ORDERS_DIR)
        self.start_day_balance_thread_start()
        self.add_positions_again_thread_start()
        if self.risk_per_trade == None and self.lot_size == None:
            return Exception("riskpertrade and lotsize both are None")
        if self.dailyrisk:
            self.daily_losslimit_check_thread_start()
            #self.threads_list.append(Periodic_Timer_Thread(interval = 10, function = self.daily_losslimit_check, comment = 'daily_losslimit_check'))
        #if self.breakeven_SL:
        #    self.threads_list.append(Periodic_Timer_Thread(interval = 60, \
        #        function = self.breakevenSL_func, comment = 'breakevenSL'))
    def daily_losslimit_check_thread_start(self):
        current_time = datetime.datetime.now()
        next_day = current_time + datetime.timedelta(seconds=5)
        next_day = datetime.datetime(year=next_day.year, month=next_day.month, day=next_day.day, hour=next_day.hour, minute=next_day.minute, second=next_day.second)
        daily_losslimit_check_event = self.scheduler_object.enterabs(time.mktime(next_day.timetuple()), 3, self.daily_losslimit_check)
        t = threading.Thread(target=self.scheduler_object.run)
        t.start()
    def start_day_balance_thread_start(self):
        
        current_time = datetime.datetime.now()
        next_day = current_time + datetime.timedelta(seconds=10)
        next_day = datetime.datetime(next_day.year, next_day.month, next_day.day, next_day.hour, next_day.minute, next_day.second)
        #next_day = current_time + datetime.timedelta(days=1)
        #next_day = datetime.datetime(year=next_day.year, month=next_day.month, day=next_day.day, hour=0, minute=0, second=10)
        daily_balance_event = self.scheduler_object.enterabs(time.mktime(next_day.timetuple()), 1, self.get_start_day_balance)
        t = threading.Thread(target=self.scheduler_object.run)
        t.start()
    def add_positions_again_thread_start(self):
        current_time = datetime.datetime.now()
        next_day = current_time + datetime.timedelta(seconds=15)
        next_day = datetime.datetime(next_day.year, next_day.month, next_day.day, next_day.hour, next_day.minute, next_day.second)
        #next_day = current_time + datetime.timedelta(days=1)
        #next_day = datetime.datetime(year=next_day.year, month=next_day.month, day=next_day.day, hour=3, minute=0, second=10)
        add_position_again_event = self.scheduler_object.enterabs(time.mktime(next_day.timetuple()), 2, self.add_position_again)
        t = threading.Thread(target=self.scheduler_object.run)
        t.start()
    def add_position_again(self):
        try:
            file_name = [name for name in os.listdir(self.PENDING_ORDERS_DIR) if os.path.isfile(os.path.join(self.PENDING_ORDERS_DIR, name))]
            print('running add_position_again at: ', datetime.datetime.now())
            if len(file_name) > 0:
                file_name.sort(key=lambda f: int(re.sub('\D', '', f)))
                file_to_open = file_name[-1]
                print('file to open: ', file_to_open)
                with open(os.path.join(self.PENDING_ORDERS_DIR, file_to_open), 'r') as f:
                    orders_in_file = json.load(f)
                    f.close()
                pending_orders = self.execute_connector_function(super().GET_ALL_POSITION_ORDERS_)['_trades']
                if pending_orders:
                    for i, (key, order_in_file_value) in enumerate(orders_in_file.items()):
                        for i, (key, pending_order_value) in enumerate(pending_orders.items()):
                            if self.check_position_exist(order_in_file_value['_type'], float(order_in_file_value['_open_price']), order_in_file_value['_symbol'], \
                                pending_order_value['_type'], float(pending_order_value['_open_price']), pending_order_value['_symbol']):
                                #print("SAME ORDER FOUNDDDDDDDDDDDDD!!!!")
                                pass
                            else:
                                trade_dict = self.execute_connector_function(super()._generate_default_order_dict)
                                trade_dict['_type'] = order_in_file_value['_type']
                                trade_dict['_symbol'] = order_in_file_value['_symbol']
                                trade_dict['_price'] = float(order_in_file_value['_open_price'])
                                trade_dict['_comment'] = order_in_file_value['_comment']
                                trade_dict['_lots'] = order_in_file_value['_lots']
                                trade_dict['_SL'] = order_in_file_value['_SL']
                                trade_dict['_TP'] = order_in_file_value['_TP']
                                self.execute_connector_function(super()._DWX_MTX_NEW_TRADE_, trade_dict)
                else:
                    for i, (key, value) in enumerate(orders_in_file.items()):
                        trade_dict = super()._generate_default_order_dict()
                        trade_dict['_type'] = int(value['_type'])
                        trade_dict['_symbol'] = value['_symbol']
                        trade_dict['_price'] = float(value['_open_price'])
                        trade_dict['_comment'] = value['_comment']
                        trade_dict['_lots'] = value['_lots']
                        trade_dict['_SL'] = value['_SL']
                        trade_dict['_TP'] = value['_TP']
                        self.execute_connector_function(super()._DWX_MTX_NEW_TRADE_, trade_dict)

            self.add_positions_again_thread_start() 
        except:
            self.add_position_again()
    def execute_connector_function(self, func, input=None,_delay=0.5,
    _wbreak=10):
        # Reset data output
        super()._set_response_(None)
        if input == None:
            func()
        else:
            func(input)
        # While loop start time reference            
        _ws = to_datetime('now')
        _response = None
        # While data not received, sleep until timeout
        while super()._valid_response_('zmq') == False:
            
            sleep(_delay)
            
            if (to_datetime('now') - _ws).total_seconds() > (_delay * _wbreak):
                break
        if super()._valid_response_('zmq'):
            _response = super()._get_response_()
        if _response == None:
            _response = {}
        #    print(_response)
        #    self.execute_connector_function(self, func, input)
        return _response


    def calculate_initial_deposit(self):
        """Calculates the initial deposit of the specified account

        Parameters
        ----------
        None

        Returns
        -------
        initial balance
        """
        func = super()._DWX_MTX_GET_DEPOSIT
        try:
            initial_balance = self.execute_connector_function(func)['deposit']
            print('initial balance: ' + str(initial_balance))
        except:
            self.calculate_initial_deposit()
        return initial_balance
    def max_loss_limit(self):
        """Calculates whether max loss limit has reached or not
        sets the self.halt_trading_completely attribute to True and closes all open trades if it is breached. 
        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        func = super().GET_CURRENT_EQUITY
        try:
            response = self.execute_connector_function(func)
            equity = response['equity']
        except:
            self.max_loss_limit()
        if equity <= self.initial_balance - (self.initial_balance * self.max_limit):
            self.halt_trading_completely = True
            print('max loss limit reached at: ', datetime.datetime.now())
            self.execute_connector_function(super()._DWX_MTX_CLOSE_ALL_TRADES_)
            
    def get_start_day_balance(self):
        """Gets the balance of the account at the start of the day
        Parameters
        ----------
        None

        Returns
        -------
        balance
        """

        func = super().GET_CURRENT_BALANCE
        try:
            response = self.execute_connector_function(func)
            balance = response['balance']
        except:
            self.get_start_day_balance()
        self.start_day_balance = balance
        print("START DAY BALANCE: ", self.start_day_balance, ' at: ', datetime.datetime.now())
        self.halt_trading_daily = False
        self.start_day_balance_thread_start()

    def daily_losslimit_check(self):
        """Checks if the daily loss limit has been reached or not
        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        try:
            if self.halt_trading_daily == False:
                func = super().GET_CURRENT_EQUITY
                response = self.execute_connector_function(func)

                equity = response['equity']
                if equity <= self.start_day_balance - (self.start_day_balance * self.daily_limit):
                    self.halt_trading_daily = True
                    print('daily loss limit reached at: ', datetime.datetime.now())
                    pending_orders = self.execute_connector_function(super().GET_ALL_POSITION_ORDERS_)['_trades']

                    index_file_name = len([name for name in os.listdir(self.PENDING_ORDERS_DIR) if os.path.isfile(os.path.join(self.PENDING_ORDERS_DIR, name))])
                    file_name = str(index_file_name) + ' ' + str(self.strategy_name)+ ' ' + str(datetime.datetime.now().replace(microsecond=0)) + '.json'
                    file_name = file_name.replace(' ', '_').replace(':', '_')
                    with open(os.path.join(self.PENDING_ORDERS_DIR, file_name), "w") as file:
                        json.dump(pending_orders, file)
                        file.close()
                    self.execute_connector_function(super()._DWX_MTX_CLOSE_ALL_TRADES_)
                    #self.halt_trading_daily = True
            print('Running daily_losslimit_check at: ', datetime.datetime.now().replace(microsecond=0))
            self.daily_losslimit_check_thread_start()
        except:
            self.daily_losslimit_check()
    def check_position_exist(self, position_type_A: int, open_price_A: float, pair_A: str, position_type_B: str, open_price_B: float, pair_B: str):
        """Checks if the position exist or not
        Parameters
        ----------
        position_type
        open_price
        pair

        Returns
        -------
        None
        """
        if pair_B.find('JPY') != -1 or pair_B.find('XAUUSD') != -1:
            round_to = 2
        else:
            round_to = 4
        test_open_price = round(float(open_price_A), round_to)
        test_open_price = round(float(open_price_B), round_to)
        if position_type_B == position_type_A and pair_B.lower() == pair_A.lower() and test_open_price == test_open_price:
            return True
        else:
            return False
    def lotsize_calculator(self, pair, sl_pips):
        """Calculates the lot size based on the SL and TP of the pair
        Parameters
        ----------
        pair
        sl_pips

        Returns
        -------
        lot_size
        """
        if pair == 'XAUUSD':
            standard_lot = 100
        else:
            standard_lot = 100000
        balance = self.execute_connector_function(super().GET_CURRENT_BALANCE)['balance']
        usd_symbols = mt5.symbols_get("*USD*")
        base_pair = pair[:3]
        quote_pair = pair[3:]
        pip_mult = mt5.symbol_info(pair).point
        if quote_pair == 'USD':
            er = 1
        elif base_pair == 'USD':
            er = 1/((mt5.symbol_info(pair).ask + mt5.symbol_info(pair).bid) / 2)
        else:
            for s in usd_symbols:
                if s.name.find(quote_pair) != -1:
                    if s.name[:3] == quote_pair:
                        #print(s.name)
                        er = (mt5.symbol_info(s.name).ask + mt5.symbol_info(s.name).bid) / 2
                    elif s.name[3:] == quote_pair:
                        #print(s.name)
                        er = 1 / ((mt5.symbol_info(s.name).ask + mt5.symbol_info(s.name).bid) / 2)
                    else:
                        raise Exception('Error in pair finding.')
        lot_size = (balance * self.riskpertrade)/((sl_pips * er) * (pip_mult * standard_lot)) / 10
        #print(lot_size)
        return round(lot_size, 2)
    def check_closed_position(self, pair, open_price):
        """Checks if the position is closed or not
        Parameters
        ----------
        pair
        open_price
        DAYS

        Returns
        -------
        None
        """
        try:
            historical_trades = self.execute_connector_function(super().GET_HISTORICAL_TRADES_)['_trades']
            for i, (ticket, value) in enumerate(historical_trades.items()):
                if value['_comment'] != "cancelled" and value['_type'] in (0, 1, 2, 3, 4, 5) and value['_symbol'] == pair and value['_open_price'] == float(open_price):
                    return True
                else:
                    return False
        except:
            self.check_closed_position(pair, open_price)

am = AccountManagement(PATH = '', strategy_name='test', dailyrisk=True, breakeven_SL=False, daily_limit=0.01, server_offset=0, start_day_balance=4830)
#am.get_gmt_offset()
while True:
    pass        
