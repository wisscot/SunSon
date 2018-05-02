# Copyright 2018 Eddy He
# Licensed under the Apache License, Version 2.0
# http://www.apache.org/licenses/LICENSE-2.0

"""
This program is to practice as a Market Maker in Korbit and Market Taker in Bithumb. 
It will check the current order book in Bithumb and place the order accordingly in Korbit.

Update data
    Step 1. Update Market data from both. 
    Step 2. Update Balance data from both. 

Initiate ASK order:

    INFO - NO ASK orders EXISTS
    
    Step X. get right price and amount of target, lower, upper
            -- check AMOUNT_MAX, on top
            -- else: check max(AMOUNT_MIN, ASK_1_AMOUNT), on top
            -- else: use AMOUNT_MAX middle price
            
    Step X. Update PO (korbit&bithumb)
            
    Step X. Check if balance is enough for PO. 
    
    Step X. Place the order.
            (update open_order id and status)

Initiate BID order: DO THE SAME


MAIN LOOP.   Monitor both orders or only one order:
    
    update market data, update balance
    if open order not exist, initiate it **
    
    update open_order status
    
    if ask fully filled, prepare bithumb PO,  
        **compensate
        update balance, record (balance/trades)
        
    if not, 
        update price amount of target/lower/higher
        if current open order not fit, 
            cancel ask order
            if cancel not success (means partial/full filled):
                **compensate
                update balance, record (balance/trades)
    
    do the same for bid
            
    wait 0.1s

Korbit API: https://apidocs.korbit.co.kr/
Korbit API wrapper:  https://github.com/HoonJin/korbit-python
 ** Korbit exchange delay issue: When submit an order to Korbit, more than 2s is needed 
   to let it show in api.list_open_orders().  When cancel the order, such wait is not needed.  
   Another way around: use view_exchange_orders function, which shows instantly
 * Korbit balance update immediately
 * Korbit exchange token needs refresh at least every 60 mins. Here its set to 10 mins.
 * Korbit exchange open orders: the number of open order can not exceed 25, otherwise 
   new order can not be placed 
 * Korbit cancel open order, will get only two status: success and not_authorized
   if order partially filled then canceled, return success

 ** Bithumb place order interval should > 4s (use 5s)
 * Bithumb balance internally after order placed
 * Bithumb seesion keeps open, reload page and update balance from server every 10 mins

THERE IS A FILL, THERE IS A CANCEL!
"""


import sys
import json
import time
import datetime
import pprint
import copy
import threading
import traceback

import korbit
# import myAPI.bithumb
# import myAPI.mongodb
# import Notification


AMOUNT_MAX = 1.0
AMOUNT_MIN = 0.001 # fixed
PRICE_INCM_BITHUMB = 1000 # fixed
PRICE_INCM_KORBIT = 500 # fixed
AMOUNT_DIGITS = 4 # bithumb restriction <=4
PRICE_CACHE = 20000
PRICE_OVER = 100000 # ensure bithumb order can fill

PROFIT_FWD = 0.001
PROFIT_BWD = 0.0005

EXCHANGE_1 = 'bithumb2'
EXCHANGE_2 = 'korbit1'

COMBINED_BTC = 14.35 #TODO

DB_CLCT = 'sunson'

BROWSER_HEADLESS = True # change to True for Linux shell


class Sunson:

    def __init__(self):
        
        self.ob = { 
            # both should be dict/json type
            'korbit': {},
            'bithumb': {}
        }
        self.ob_threads = {
            'kobit_stop': False,
            'bithumb_stop': False
        }
            
        self.price = { # all int type
            'korbit':{
                'ask':{
                    'ask_1': None,
                    'target': None,
                    'lower': None,
                    'upper': None,
                    'PO': None
                },
                'bid':{
                    'bid_1': None,
                    'target': None,
                    'lower': None,
                    'upper': None,
                    'PO': None
                }
            },
            'bithumb':{
                'buy': {
                    'intend': None,
                    'PO': None
                },
                'sell': {
                    'intend': None,
                    'PO': None
                }
            }    
        }
          
        self.amount = copy.deepcopy(self.price)

        self.profit = {
            'fwd': PROFIT_FWD,
            'bwd': PROFIT_BWD,
        }

        self.balance = { # all float
            'korbit':{
                'krw':{'total':None, 'available':None},
                'btc':{'total':None, 'available':None}
            },
            'bithumb':{
                'krw':{'total':None, 'available':None},
                'btc':{'total':None, 'available':None}
            }
        }

        self.open_order = {
            'ask':{
                'id': None, # str type
                'response': None, 
                'filled_amount': None, # float
                'is_filled': False        # this means fully filled
            },
            'bid':{
                'id': None,
                'response': None,
                'filled_amount': None,
                'is_filled': False        
            }
        }

        self.trade_record = {
            'datetime': None,
            EXCHANGE_1: {
                'balance_before_trade':{
                    'btc': None,
                    'krw': None
                },
                'trade':{
                    'action': None,
                    'price': None,
                    'amount': None                
                }
            }
        }
        self.trade_record[EXCHANGE_2] = copy.deepcopy(self.trade_record[EXCHANGE_1])
        
        self.servers_status = {
            'times_failed': 0,
            'is_down': False,
            'back_to_live': True
        }
        
        self.bithumb_PO_timer = time.time()
        
        self.timestamp = {
            'korbit_filled': None,
            'place_bithumb_order': None
        }
        
        self.korbit_api = None
        self.bithumb_client = None
        self.bithumb_public = None

    def init_exchanges_sessions(self, secrets):
        
        # create korbit session
        self.korbit_api = korbit.PrivateAPI(client_id = secrets[EXCHANGE_2]['key'], 
                                       secret = secrets[EXCHANGE_2]['secret'],
                                       timeout=20)
        self.korbit_api.create_token_directly(username = secrets[EXCHANGE_2]['email'], 
                                         password = secrets[EXCHANGE_2]['password'])

        # create bithumb session
        self.bithumb_client = myAPI.bithumb.bithumb_browser(secrets[EXCHANGE_1]['user'], 
                                                       secrets[EXCHANGE_1]['pwd'], 
                                                       secrets[EXCHANGE_1]['OTP_key'],
                                                       headless = BROWSER_HEADLESS)
        self.bithumb_client.login()
        self.bithumb_client.goto_trade_page()        
        if not self.bithumb_client.is_logged_in(): # verify loggedin
            print('\nBithumb Login Failed!\n')
            raise RuntimeError('Ooops... bithumb browser initiate error')
        self.bithumb_public = myAPI.bithumb.Public()

    def update_korbit_ob_in_background(self):
        '''
        self.ob['korbit'] = {
          "timestamp" : 1386135077000,
          "bids" : [["1100000", "0.0103918", "1"], ["1000000", "0.01000000", "1"], ... ],
          "asks" : [["569000", "0.50000000", "1"], ["568500", "2.00000000", "1"], ... ]
        }        
        '''
        self.ob['korbit']['timestamp'] = 0
        while True:
            if self.ob_threads['kobit_stop']: 
                self.ob_threads['kobit_stop'] = False
                break
            try:
                korbit_ob = self.korbit_api.orderbook()
                if not 'timestamp' in korbit_ob:
                    raise RuntimeError('Ooops... no timestamp in response')
                if int(korbit_ob['timestamp']) < int(self.ob['korbit']['timestamp']): continue
                self.ob['korbit'] = korbit_ob
            except:
                pass
            
            self.price['korbit']['ask']['ask_1'] = int(self.ob['korbit']['asks'][0][0])
            self.amount['korbit']['ask']['ask_1'] = float(self.ob['korbit']['asks'][0][1])        
            self.price['korbit']['bid']['bid_1'] = int(self.ob['korbit']['bids'][0][0])
            self.amount['korbit']['bid']['bid_1'] = float(self.ob['korbit']['bids'][0][1])
            
            time.sleep(0.4)
            
    def update_bithumb_ob_in_background(self):
        '''
        self.ob['bithumb'] = {
            'asks': [{'price': '11654000', 'quantity': '0.19900000'},{},... ],
            'bids': [],
            'timestamp': 12345678
        }
        ''' 
        while True:
            if self.ob_threads['bithumb_stop']: 
                self.ob_threads['bithumb_stop'] = False
                break
            try:
                self.bithumb_public.update_ob()
                bithumb_ob = self.bithumb_public.ob
                self.ob['bithumb'] = bithumb_ob['data']
            except:
                pass
                
    def update_market_data_depreciated(self):
        '''
        update order book from bithumb and korbit
        '''
        
        self.bithumb_public.update_ob()
        self.ob['bithumb'] = self.bithumb_public.ob['data']
        '''
        self.ob['bithumb'] = {
            'asks': [{'price': '11654000', 'quantity': '0.19900000'},{},... ],
            'bids': [],
            'timestamp': 12345678
        }
        '''        
        
        self.ob['korbit'] = self.korbit_api.orderbook()
        '''
        self.ob['korbit'] = {
          "timestamp" : 1386135077000,
          "bids" : [["1100000", "0.0103918", "1"], ["1000000", "0.01000000", "1"], ... ],
          "asks" : [["569000", "0.50000000", "1"], ["568500", "2.00000000", "1"], ... ]
        }        
        '''
        self.price['korbit']['ask']['ask_1'] = int(self.ob['korbit']['asks'][0][0])
        self.amount['korbit']['ask']['ask_1'] = float(self.ob['korbit']['asks'][0][1])        
        self.price['korbit']['bid']['bid_1'] = int(self.ob['korbit']['bids'][0][0])
        self.amount['korbit']['bid']['bid_1'] = float(self.ob['korbit']['bids'][0][1])
        
    def update_balance_data(self, internal=False, side=None):
        '''
        update balance from bithumb and korbit
        '''
        
        # Bithumb:
        if internal == False:
            bithumb_balance = self.bithumb_client.get_balance_quick()
            self.balance['bithumb']['btc']['total'] = bithumb_balance['btc']['total']
            self.balance['bithumb']['krw']['total'] = bithumb_balance['krw']['total']
            
            self.balance['bithumb']['btc']['available'] = bithumb_balance['btc']['available']
            self.balance['bithumb']['krw']['available'] = bithumb_balance['krw']['available']
            '''
            bithumb_balance = {'btc': balance_btc, 'krw': balance_krw} #float
            '''
        else:
            assert side == 'buy' or side == 'sell'
            if side == 'buy':
                self.balance['bithumb']['btc']['total'] += self.amount['bithumb']['buy']['PO']
                self.balance['bithumb']['krw']['total'] -= (self.amount['bithumb']['buy']['PO']*
                                                            self.price['bithumb']['buy']['intend'])
            else:
                self.balance['bithumb']['btc']['total'] -= self.amount['bithumb']['sell']['PO']
                self.balance['bithumb']['krw']['total'] += (self.amount['bithumb']['sell']['PO']*
                                                            self.price['bithumb']['sell']['intend'])
                
            self.balance['bithumb']['btc']['available'] = self.balance['bithumb']['btc']['total']                                            
            self.balance['bithumb']['krw']['available'] = self.balance['bithumb']['krw']['total']                                            
        
        # Korbit:
        if internal == False:
            korbit_balance = self.korbit_api.user_balances()
            self.balance['korbit']['btc']['available'] = float(korbit_balance['btc']['available'])
            self.balance['korbit']['krw']['available'] = float(korbit_balance['krw']['available'])
            self.balance['korbit']['btc']['total'] = (float(korbit_balance['btc']['trade_in_use']) +
                                                        self.balance['korbit']['btc']['available'] )
            self.balance['korbit']['krw']['total'] = (float(korbit_balance['krw']['trade_in_use']) +
                                                        self.balance['korbit']['krw']['available'] )
            """
            korbit_balance = {
              "krw" : {
                  "available" : "123000",
                  "trade_in_use" : "13000",
                  "withdrawal_in_use" : "0"
              },
              "btc" : {
                  "available" : "1.50200000",
                  "trade_in_use" : "0.42000000",
                  "withdrawal_in_use" : "0.50280000"
              },"ltc"...    
            """
        else:
            assert side == 'buy' or side == 'sell'
            if side == 'buy':
                self.balance['korbit']['btc']['total'] -= self.amount['bithumb']['buy']['PO']
                self.balance['korbit']['krw']['total'] += (self.amount['bithumb']['buy']['PO']*
                                                            self.price['korbit']['ask']['PO'])
            else:
                self.balance['korbit']['btc']['total'] += self.amount['bithumb']['sell']['PO']
                self.balance['korbit']['krw']['total'] -= (self.amount['bithumb']['sell']['PO']*
                                                            self.price['korbit']['bid']['PO'])
                
            self.balance['korbit']['btc']['available'] = self.balance['korbit']['btc']['total']                                            
            self.balance['korbit']['krw']['available'] = self.balance['korbit']['krw']['total']                                            
                
    def update_open_order_status_depreciated(self):
        
        korbit_open_orders = self.korbit_api.list_open_orders(limit=5)
        """
        returned value:
        [{'id': '16184756',
          'native_total': {'currency': 'krw', 'value': '18920'},
          'open': {'currency': 'btc', 'value': '0.001'},
          'price': {'currency': 'krw', 'value': '18920000'},
          'timestamp': 1515942680437,
          'total': {'currency': 'btc', 'value': '0.001'},
          'type': 'bid'},  
          {...}, ...]
        """
        id_resp = {ood['id']: ood for ood in korbit_open_orders}
        # debug:
        # pprint.pprint('id_response = ', id_resp)
        
        ask_id = self.open_order['ask']['id']
        if ask_id:
            
            if not ask_id in list(id_resp):
                self.open_order['ask']['filled_amount'] = 0
                self.open_order['ask']['is_filled'] = True
            else:
                self.open_order['ask']['response'] = id_resp[ask_id]
                self.open_order['ask']['filled_amount'] = float(id_resp[ask_id]['open']['value'])
                self.open_order['ask']['is_filled'] = abs(self.open_order['ask']['filled_amount'] 
                                    - self.amount['korbit']['ask']['PO']) >= AMOUNT_MIN
            
        bid_id = self.open_order['bid']['id']
        if bid_id:
            if not bid_id in list(id_resp):
                self.open_order['bid']['filled_amount'] = 0
                self.open_order['bid']['is_filled'] = True
            else:
                self.open_order['bid']['response'] = id_resp[bid_id]
                self.open_order['bid']['filled_amount'] = float(id_resp[bid_id]['open']['value'])
                self.open_order['bid']['is_filled'] = abs(self.open_order['bid']['filled_amount'] 
                                    - self.amount['korbit']['bid']['PO']) >= AMOUNT_MIN
            
    def cancel_all_open_orders(self):
        '''
        cancel all korbit open orders 
        '''
        korbit_open_orders = self.korbit_api.list_open_orders(limit=10)
        ids = [korbit_open_order['id'] for korbit_open_order in korbit_open_orders]
        self.korbit_api.cancel_order(ids = ids)
    
    def update_open_order_status(self, side):        
        ''' 
        return : 
        [{'avg_price': '12565500',
          'created_at': 1520132754687,
          'currency_pair': 'btc_krw',
          'fee': '6',
          'filled_amount': '0.002',
          'filled_total': '25131',
          'id': '19983795',
          'last_filled_at': 1520133362604,
          'order_amount': '1',
          'order_total': '12565500',
          'price': '12565500',
          'side': 'ask',
          'status': 'filled'}]      
        if an open order is cancelled, the status is filled for partially filled order
        '''      
        assert side == 'buy' or side == 'sell'        
        ask_or_bid = 'ask' if side == 'buy' else 'bid'
        
        ids = [self.open_order[ask_or_bid]['id']]
        
        try:
            response = self.korbit_api.view_exchange_orders(ids) # ids is a str list
        except:
            error_log('update_open_order_status error')
            return False
        
        if response == []: 
            #means the order has been canceled and no any filled 
            self.open_order[ask_or_bid]['is_filled'] = False
            return True
        elif response == '':
            # means session was login somewhere else
            error_log('update_open_order_status response is empty string')
            return False
        elif len(response) > 1:
            error_log('update_open_order_status response is: ' + str(response))
            return False
            
            
        assert len(response) == 1
        
        response = response[0]
        
        if not 'status' in response:
            error_log('update_open_order_status response not has "status"')
            return False
        
        status = response['status']
        assert status in ['filled', 'partially_filled', 'unfilled']
        
        filled_amount = float(response['filled_amount'])
        
        #TODO: cambine filled and partially filled
        if status == 'filled':                    
            if filled_amount >= AMOUNT_MIN:
                self.open_order[ask_or_bid]['is_filled'] = True
            else:
                self.open_order[ask_or_bid]['is_filled'] = False
            
        elif status == 'partially_filled':        
            # if filled_amount < AMOUNT_MIN: filled_amount = AMOUNT_MIN
            # self.open_order[ask_or_bid]['is_filled'] = False
            if filled_amount >= AMOUNT_MIN:
                self.open_order[ask_or_bid]['is_filled'] = True
            else:
                self.open_order[ask_or_bid]['is_filled'] = False
            
        elif status == 'unfilled':
            self.open_order[ask_or_bid]['is_filled'] = False
            #debug:
            assert filled_amount == 0.0
            
        self.open_order[ask_or_bid]['filled_amount'] = filled_amount
        self.open_order[ask_or_bid]['response'] = response
        
        return True
            
    def update_target_price(self, side):
        '''
        get bithumb ob and calculate right price and amount of target, lower, upper
        '''
        assert side == 'buy' or side == 'sell'

        # if on order book top        
        def set_buy_side_for_top(self, price, amount, korbit_price):
            self.price['bithumb']['buy']['intend'] = price['buy']
            self.amount['bithumb']['buy']['intend'] = amount['buy']
        
            self.price['korbit']['ask']['target'] = korbit_price['ask']
            self.amount['korbit']['ask']['target'] = amount['buy']
        
            self.price['korbit']['ask']['lower'] = max( self.price['korbit']['ask']['ask_1'] - PRICE_INCM_KORBIT,
                                                     self.price['korbit']['bid']['bid_1'] + PRICE_INCM_KORBIT)
            if self.amount['korbit']['ask']['ask_1'] < amount['buy']:
                self.price['korbit']['ask']['lower'] = self.price['korbit']['ask']['ask_1']
            self.amount['korbit']['ask']['lower'] = amount['buy']
    
            self.price['korbit']['ask']['upper'] = self.price['korbit']['ask']['lower'] + PRICE_CACHE 
            self.amount['korbit']['ask']['upper'] = amount['buy']
    
        def set_sell_side_for_top(self, price, amount, korbit_price):
            self.price['bithumb']['sell']['intend'] = price['sell']
            self.amount['bithumb']['sell']['intend'] = amount['sell']
    
            self.price['korbit']['bid']['target'] = korbit_price['bid']
            self.amount['korbit']['bid']['target'] = amount['sell']
        
            self.price['korbit']['bid']['upper'] = min( self.price['korbit']['bid']['bid_1'] + PRICE_INCM_KORBIT,
                                                     self.price['korbit']['ask']['ask_1'] - PRICE_INCM_KORBIT)
            if self.amount['korbit']['bid']['bid_1'] < amount['sell']:
                self.price['korbit']['bid']['upper'] = self.price['korbit']['bid']['bid_1']
            self.amount['korbit']['bid']['upper'] = amount['sell']
    
            self.price['korbit']['bid']['lower'] = self.price['korbit']['bid']['upper'] - PRICE_CACHE 
            self.amount['korbit']['bid']['lower'] = amount['sell']
        
        # if not on order book top
        def set_buy_side_for_no_top(self, price, amount, korbit_price):
        
            set_buy_side_for_top(self, price, amount, korbit_price)
        
            self.price['korbit']['ask']['lower'] = self.price['korbit']['ask']['target']
            self.price['korbit']['ask']['upper'] = self.price['korbit']['ask']['lower'] + PRICE_CACHE 
    
        def set_sell_side_for_no_top(self, price, amount, korbit_price):
    
            set_sell_side_for_top(self, price, amount, korbit_price)
            
            self.price['korbit']['bid']['upper'] = self.price['korbit']['bid']['target']
            self.price['korbit']['bid']['lower'] = self.price['korbit']['bid']['upper'] - PRICE_CACHE 
        
        if side == 'buy':
        
            # if btc balance low, buy more, otherwise buy less
            bithumb_portion = self.balance['bithumb']['btc']['total'] / (self.balance['bithumb']['btc']['total']
                                                                        +self.balance['korbit']['btc']['total'])
            if bithumb_portion < 0.2:
                self.profit['fwd'] = PROFIT_FWD + 0.0015*(bithumb_portion*2-1)
            elif bithumb_portion > 0.6:
                self.profit['fwd'] = PROFIT_FWD + 0.0015*(bithumb_portion*2-1)
            else:
                self.profit['fwd'] = PROFIT_FWD
            
            amt = AMOUNT_MAX/1
            assert amt >= AMOUNT_MIN
            
            for buy_amt in [amt]:
            # for buy_amt in [AMOUNT_MAX, max(AMOUNT_MIN, self.amount['korbit']['ask']['ask_1']), AMOUNT_MAX]:
                
                amount = {'buy': buy_amt, 'sell': None}
                price = self.bithumb_public.eqv_price(amount) # float
                price = { x : format_price(price[x], exch = 'bithumb') for x in price if price[x]} # convert float to int
                '''price = {'buy': int }'''
        
                korbit_price = {'ask': format_price( price['buy']*(1 + self.profit['fwd']), exch = 'korbit')} # int type
                
                # if on top:
                if korbit_price['ask'] < self.price['korbit']['ask']['ask_1']:
                
                    set_buy_side_for_top(self, price, amount, korbit_price)
                    return
                
                # if not on top
                set_buy_side_for_no_top(self, price, amount, korbit_price)

        if side == 'sell':   
            korbit_portion = self.balance['korbit']['btc']['total'] / (self.balance['bithumb']['btc']['total']
                                                                        +self.balance['korbit']['btc']['total'])
            if korbit_portion < 0.2:
                self.profit['bwd'] = PROFIT_BWD  + 0.0015*(korbit_portion*2-1)
            elif korbit_portion > 0.6:
                self.profit['bwd'] = PROFIT_BWD  + 0.0015*(korbit_portion*2-1)
            else:
                self.profit['bwd'] = PROFIT_BWD
            
            amt = AMOUNT_MAX/1
            assert amt >= AMOUNT_MIN

            for sell_amt in[amt]:    
            # for sell_amt in[AMOUNT_MAX, max(AMOUNT_MIN, self.amount['korbit']['bid']['bid_1']), AMOUNT_MAX]:    
                
                amount = {'buy': None, 'sell': sell_amt}
                price = self.bithumb_public.eqv_price(amount)
                price = { x : format_price(price[x], exch = 'bithumb') for x in price if price[x]} # convert all float to int
                '''price = {'sell': int }'''
                
                korbit_price = { # all int type
                    'ask': None,
                    'bid': format_price( price['sell']/(1 + self.profit['bwd']), exch = 'korbit' )
                }
                
                # if on top:
                if korbit_price['bid'] > self.price['korbit']['bid']['bid_1']:
            
                    set_sell_side_for_top(self, price, amount, korbit_price)
                    return
                            
                # if not on top
                set_sell_side_for_no_top(self, price, amount, korbit_price)
    
    def update_PO(self, side):
        '''
        update PO for bithumb and korbit
        '''
        assert side == 'buy' or side == 'sell'
        
        if side == 'buy': 
            
            self.price['bithumb']['buy']['PO'] = self.price['bithumb']['buy']['intend'] + PRICE_OVER
            self.amount['bithumb']['buy']['PO'] = format_amount(self.amount['bithumb']['buy']['intend'])
        
            if self.price['korbit']['ask']['target']/(1 + self.profit['fwd']) < self.price['korbit']['bid']['bid_1']*0.995:
                
                self.price['korbit']['ask']['PO'] = self.price['korbit']['bid']['bid_1']
            
            elif self.price['korbit']['ask']['target'] < self.price['korbit']['ask']['ask_1']:
            
                self.price['korbit']['ask']['PO'] = self.price['korbit']['ask']['lower']

            else:
            
                self.price['korbit']['ask']['PO'] = format_price((self.price['korbit']['ask']['lower'] 
                                                + self.price['korbit']['ask']['upper']) /2, 
                                                exch = 'korbit')
            self.amount['korbit']['ask']['PO'] = format_amount(self.amount['korbit']['ask']['lower'])
                
        if side == 'sell':
            
            self.price['bithumb']['sell']['PO'] = self.price['bithumb']['sell']['intend'] - PRICE_OVER
            self.amount['bithumb']['sell']['PO'] = format_amount(self.amount['bithumb']['sell']['intend'])

            if self.price['korbit']['bid']['target']*(1 + self.profit['bwd']) > self.price['korbit']['ask']['ask_1']*1.005:
            
                self.price['korbit']['bid']['PO'] = self.price['korbit']['ask']['ask_1']

            elif self.price['korbit']['bid']['target'] > self.price['korbit']['bid']['bid_1']:
            
                self.price['korbit']['bid']['PO'] = self.price['korbit']['bid']['upper']
                self.amount['korbit']['bid']['PO'] = format_amount(self.amount['korbit']['bid']['upper'])
                
            else:
            
                self.price['korbit']['bid']['PO'] = format_price((self.price['korbit']['bid']['lower'] 
                                                + self.price['korbit']['bid']['upper']) /2, 
                                                exch = 'korbit')
                self.amount['korbit']['bid']['PO'] = format_amount(self.amount['korbit']['bid']['upper'])
                
    def is_balance_enough(self, side):
        '''
        check if balance enough for bithumb and korbit
        '''
        assert side == 'buy' or side == 'sell'
        
        if side == 'buy': 
            if self.balance['bithumb']['krw']['available'] < ( self.price['bithumb']['buy']['PO'] *
                                                            self.amount['bithumb']['buy']['PO']):
                return False
            if self.balance['korbit']['btc']['available'] < self.amount['korbit']['ask']['PO']:
                return False
        
        if side == 'sell': 
            if self.balance['bithumb']['btc']['available'] < self.amount['bithumb']['sell']['PO']:
                return False
            if self.balance['korbit']['krw']['available'] < ( self.price['korbit']['bid']['PO'] *
                                                                self.amount['korbit']['bid']['PO']):
                return False
                
        return True
            
    def place_open_order(self, side):
        '''
        response = {
          "orderId":58738,
          "status":"success",
          "currency_pair":"btc_krw"
        }'''           
        assert side == 'buy' or side == 'sell'
        ask_or_bid = 'ask' if side == 'buy' else 'bid'

        if side == 'buy':
            price = str( self.price['korbit']['ask']['PO'] )
            amount = str( self.amount['korbit']['ask']['PO'] )
            response = None
            try:
                response = self.korbit_api.limit_ask_order(amount, price)
            except:
                error_log('kobit place ask order error, response = ' + str(response))
                return
                
        if side == 'sell':
            price = str( self.price['korbit']['bid']['PO'] )
            amount = str( self.amount['korbit']['bid']['PO'] )
            response = None
            try:
                response = self.korbit_api.limit_bid_order(amount, price)
            except:
                error_log('kobit place ask order error, response = ' + str(response))
                return
        
        if not 'status' in response:
            return
            
        # check for response
        if response['status'] == 'success':
            self.open_order[ask_or_bid]['response'] = response
            self.open_order[ask_or_bid]['id'] = str(response['orderId']) # str type
            self.open_order[ask_or_bid]['filled_amount'] = 0.0 # float type
            self.open_order[ask_or_bid]['is_filled'] = False
        else:
            raise RuntimeError('Ooops... place_open_order response shows failed...')            
            
    def initiate_open_order(self, side):
        '''
        plance korbit open order, can handle not enough balance
        '''
        assert side == 'buy' or side == 'sell'

        self.update_target_price(side)
        self.update_PO(side)
        if self.is_balance_enough(side):
            self.place_open_order(side)
            # time.sleep(2) # not needed because update_balance use new method
        else:
            print('not enough balance')

    def is_open_order_filled(self, side):

        assert side == 'buy' or side == 'sell'
        
        if side == 'buy':
            return self.open_order['ask']['is_filled']
        
        if side == 'sell':
            return self.open_order['bid']['is_filled']

    def is_open_order_still_fits(self, side):

        assert side == 'buy' or side == 'sell'

        if side == 'buy' and self.open_order['ask']['id']:
            if (self.price['korbit']['ask']['target'] < self.price['korbit']['ask']['ask_1'] and
                self.price['korbit']['ask']['PO'] > self.price['korbit']['ask']['ask_1'] ):
                return False
            if (self.price['korbit']['ask']['PO'] > self.price['korbit']['ask']['upper']
                or self.price['korbit']['ask']['PO'] < self.price['korbit']['ask']['lower']):
                return False
        
        if side == 'sell' and self.open_order['bid']['id']:
            if (self.price['korbit']['bid']['target'] > self.price['korbit']['bid']['bid_1'] and
                self.price['korbit']['bid']['PO'] < self.price['korbit']['bid']['bid_1'] ):
                return False
            if (self.price['korbit']['bid']['PO'] > self.price['korbit']['bid']['upper']
                or self.price['korbit']['bid']['PO'] < self.price['korbit']['bid']['lower']):
                return False
        
        return True
                
    def cancel_open_order(self, side):
        '''
        korbit api return 
        [
          {"orderId":"1000","status":"success"},
        ] 
        status = success, not_found, not_authorized, 
                 already_filled, partially_filled, already_canceled ... 
        '''      
        assert side == 'buy' or side == 'sell'        
        ask_or_bid = 'ask' if side == 'buy' else 'bid'
        
        if self.open_order[ask_or_bid]['id'] is None:
            return
                    
        ids = [ self.open_order[ask_or_bid]['id'] ]
        try:
            response = self.korbit_api.cancel_order(ids) # ids is a str list
        except:
            time.sleep(10)
            error_log('Ooops... cancel order error')
            return False
            
        #debug
        print('cancel openorder response=', response)

        if len(response) != 1: 
            time.sleep(10)
            return False
        
        response = response[0]                
        
        self.open_order[ask_or_bid]['response'] = response

        if not 'status' in response: 
            time.sleep(10)
            return False
        
        if response['status'] != 'success': 
            error_log('Ooops... cancel open order response[status]: '+ response['status'])
            
        return True
        
    def reset_open_order_status(self, side):

        assert side == 'buy' or side == 'sell'        
        ask_or_bid = 'ask' if side == 'buy' else 'bid'
        
        self.open_order[ask_or_bid]['id'] = None
        self.open_order[ask_or_bid]['filled_amount'] = None
        self.open_order[ask_or_bid]['is_filled'] = False
        self.open_order[ask_or_bid]['response'] = None
        
    def prepare_bithumb_PO(self, side):

        assert side == 'buy' or side == 'sell'

        if side == 'buy':
            
            self.price['bithumb']['buy']['PO'] = self.price['bithumb']['buy']['intend'] + PRICE_OVER
            self.amount['bithumb']['buy']['PO'] = self.open_order['ask']['filled_amount']
                
        if side == 'sell':
            
            self.price['bithumb']['sell']['PO'] = self.price['bithumb']['sell']['intend'] - PRICE_OVER
            self.amount['bithumb']['sell']['PO'] = self.open_order['bid']['filled_amount']
            
    def place_bithumb_order(self, side):

        assert side == 'buy' or side == 'sell'
        
        # Bithumb place order interval should not less than 4s (use 5s)
        while time.time() - self.bithumb_PO_timer < 5:
            time.sleep(1)
        self.bithumb_PO_timer = time.time()

        if side == 'buy':
            
            price = str(self.price['bithumb']['buy']['PO'])
            amount = str(format_amount(self.amount['bithumb']['buy']['PO']))
            
            success, msg_1, msg_2 = self.bithumb_client.buy(price, amount)
            times_trial = 0
            while not success:
                times_trial += 1                
                if times_trial >= 5: 
                    raise RuntimeError('Ooops... bithumb buy failed 5 times in a row')

                self.bithumb_client.refresh()
                error_log('bithumb buy failed, retrying... \n msg_1: {}  msg_2: {}'.format(msg_1, msg_2))
                time.sleep(5)
                
                success, msg_1, msg_2 = self.bithumb_client.buy(price, amount)
                
        if side == 'sell':

            price = str(self.price['bithumb']['sell']['PO'])
            amount = str(format_amount(self.amount['bithumb']['sell']['PO']))
            
            success, msg_1, msg_2 = self.bithumb_client.sell(price, amount)
            
            times_trial = 0
            while not success:
                times_trial += 1                
                if times_trial >= 5: 
                    raise RuntimeError('Ooops... bithumb sell failed 5 times in a row')

                self.bithumb_client.refresh()
                error_log('bithumb sell failed, retrying... \n msg_1: {}  msg_2: {}'.format(msg_1, msg_2))
                time.sleep(5)
                
                success, msg_1, msg_2 = self.bithumb_client.sell(price, amount)
            
    def compensate(self, side):
    
        print('****')
        print('**compensate {} side**'.format(side))
        print('****')

        assert side == 'buy' or side == 'sell'        
        ask_or_bid = 'ask' if side == 'buy' else 'bid'

        self.prepare_bithumb_PO(side)
        self.place_bithumb_order(side)
        # time.sleep(1) # TODO: any way to get around this
        self.update_balance_data(internal=True, side=side)
        self.record_trade(side)
        
        self.reset_open_order_status(side)
        
    def retreat(self, side):

        assert side == 'buy' or side == 'sell' or side == 'both'
        if side == 'both':
            self.retreat('buy')
            self.retreat('sell')
            return
        
        ask_or_bid = 'ask' if side == 'buy' else 'bid'

        if not self.open_order[ask_or_bid]['id']: return
        
        # cancel open orders 
        # if cancel failed, then do not reset open order status
        success = self.cancel_open_order(side) 
        if not success: return
        
        self.update_open_order_status(side)
        if self.is_open_order_filled(side): # fully filled or partially filled
            self.compensate(side)

        self.reset_open_order_status(side)
    
    def record_trade(self, side):

        assert side == 'buy' or side == 'sell'    

        if side == 'buy':
            op_side = 'sell'
            bid_or_ask = 'ask'
                
        if side == 'sell':
            op_side = 'buy'
            bid_or_ask = 'bid'

        self.trade_record = {
            'datetime': datetime.datetime.utcnow(),
            EXCHANGE_1: { # Bithumb
                'balance_before_trade':{
                    'btc': self.balance['bithumb']['btc']['total'],
                    'krw': self.balance['bithumb']['krw']['total']
                },
                'trade':{
                    'action': side,
                    'price': self.price['bithumb'][side]['intend'],
                    'amount': self.amount['bithumb'][side]['PO']                
                }
            },
            EXCHANGE_2: { # Korbit
                'balance_before_trade':{
                    'btc': self.balance['korbit']['btc']['total'],
                    'krw': self.balance['korbit']['krw']['total']
                },
                'trade':{
                    'action': op_side,
                    'price': self.price['korbit'][bid_or_ask]['PO'],
                    'amount': self.amount['bithumb'][side]['PO']
                }
            }
        }
        
        try:
            myAPI.mongodb.save_to_db(DB_CLCT, self.trade_record)
        except:    
            Notification.send_email(subject = 'SunSon write to mongodb failed')
        
    def refresh_bithumb(self):
        '''
        refresh bithumb web page, if its not logged in, then try log in again
        waiting time is 1, 2, 4, 8, 16... seconds
        '''
        try:
            self.bithumb_client.refresh()   
            is_logged_in = self.bithumb_client.is_logged_in()
            self.update_balance_data()
        except:
            pass
        if not is_logged_in:
            print('relogin...')
            error_log('SS.bithumb_client.refresh() error, relogin')
            times_failed = 0
            while not self.bithumb_client.is_logged_in():
                self.bithumb_client.logout(browser_quit=False)
                try:
                    self.bithumb_client.login()
                except:
                    pass
                self.bithumb_client.goto_trade_page()
                print('bithumb login failed, waiting #', times_failed)
                time.sleep(60*(2**times_failed -1))
                times_failed += 1

            
def format_price(price, exch):
    '''
    format price to PRICE_INCM_BITHUMB = 1000
    '''
    if exch == 'bithumb':
        return round(price/PRICE_INCM_BITHUMB) * PRICE_INCM_BITHUMB 
    elif exch == 'korbit':
        return round(price/PRICE_INCM_KORBIT) * PRICE_INCM_KORBIT
    
def format_amount(amount):
    '''
    format amount to AMOUNT_DIGITS = 4
    '''
    return round(amount*10**AMOUNT_DIGITS) / 10**AMOUNT_DIGITS

def error_log(msg):
    '''
    write error log to mongodb
    '''
    try:
        myAPI.mongodb.save_to_db('SunsonError', {
            'datetime': datetime.datetime.utcnow(),
            'msg': msg
        })
    except:    
        Notification.send_email(subject = 'SunSon write to mongodb failed')
    
def run(SS):

    # set a timer to refresh sessions for both exchanges
    korbit_fresh_time = int(time.time()/(60*10)) + 1
    bithumb_fresh_time = int(time.time()/(60*10)) + 1
    
    # create thread for updating bithumb ob data
    bithumb_ob_thread = threading.Thread(target= SS.update_bithumb_ob_in_background)
    bithumb_ob_thread.start()

    # create thread for updating korbit ob data
    korbit_ob_thread = threading.Thread(target= SS.update_korbit_ob_in_background)
    korbit_ob_thread.start()
    
    print('waiting for ob threads warm up...  5s...')
    time.sleep(5) # for bithumb and korbit ob threads warm up
    
    # update balance from servers
    SS.update_balance_data()
    
    # cancel existing open orders
    SS.cancel_all_open_orders()
    
    while True:
    
        # main LOOP 
        
        # make sure two ob threads are alive 
        if not korbit_ob_thread.is_alive():
            raise RuntimeError('Ooops... korbit ob thread broke')
        if not bithumb_ob_thread.is_alive():
            raise RuntimeError('Ooops... bithumb ob thread broke')
        korbit_ob_delay = time.time() - float(SS.ob['korbit']['timestamp'])/1e3
        bithumb_ob_delay = time.time() - float(SS.ob['bithumb']['timestamp'])/1e3
        print('korbit_ob_delay = ', korbit_ob_delay)
        print('bithumb_ob_delay = ', bithumb_ob_delay)
            
        # if the ob delay too much, retreat
        if korbit_ob_delay > 11 or bithumb_ob_delay > 6:
            print('\nMAIN LOOP update ob delayed > 11s !! \n')
            SS.retreat('both')                 
            time.sleep(0.1)
            continue

        # place order if no open order exists
        if not SS.open_order['ask']['id']: 
            SS.initiate_open_order(side = 'buy')
        if not SS.open_order['bid']['id']: 
            SS.initiate_open_order(side = 'sell')
        
        # watching the open orders, take action if necessary
        for side in ['buy', 'sell']:
                    
            # if no open order, then skip
            ask_or_bid = 'ask' if side == 'buy' else 'bid'
            if not SS.open_order[ask_or_bid]['id']: continue
            
            #debug
            print('updating open order status')
            success = SS.update_open_order_status(side)
            if not success: 
                print('---------retreat----------')
                SS.retreat('both')
                break
            print('updating open order status done')
            
            if SS.is_open_order_filled(side): # fully/partially filled 
                # SS.compensate(side)
                SS.retreat(side) 
            
            else:
                SS.update_target_price(side)
                if SS.is_open_order_still_fits(side):
                    continue
                else:
                    print('current {} order not fit any more'.format(side))
                    SS.retreat(side) 
                    

        # refresh korbit sessions at 10 mins interval
        if int(time.time()/(60*10)) >= korbit_fresh_time:
            korbit_fresh_time += 1
            print('korbit seesions refreshing at 10 mins interval')
            SS.korbit_api.refresh_token()
        
        # refresh bithumb session at 10 mins interval
        if int(time.time()/(60*10)) >= bithumb_fresh_time:
            bithumb_fresh_time += 1
            print('bithumb seesions refreshing at 10 mins interval')
            SS.retreat('both') 
            SS.refresh_bithumb() # refresh balance from servers included (korbit&bithumb)
            
        time.sleep(0.5) # TODO: can be tweaked later
        
        # screen output
        print(time.ctime())
        print('price = ')
        pprint.pprint(SS.price)
        print('amount = ')
        pprint.pprint(SS.amount)
        print('balance = ')
        pprint.pprint(SS.balance)
        # print('open_order = ')
        # pprint.pprint(SS.open_order)
        # print('bithumb ob = ')
        # pprint.pprint(SS.bithumb_public.ob['data']['asks'][0])
        # pprint.pprint(SS.bithumb_public.ob['data']['bids'][0])
        print()
        # debug: sys.exit(1)
            
            
def main():

    # read secrets.json file
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
            
    tried_time = 1
    while True:
        
        if tried_time > 1: break
        reboot_interval = 60**tried_time
        
        try:
            # create main class
            SS = Sunson()
            SS.init_exchanges_sessions(secrets)       
            # run
            run(SS)
        except:
            SS.ob_threads['kobit_stop'] = True
            SS.ob_threads['bithumb_stop'] = True
            if SS.bithumb_client: SS.bithumb_client.browser.quit()

            Notification.send_email(subject = 'SunSon Stopped and restarting')
            Notification.send_email(subject = 'SunSon Stopped and restarting',
                                    recipient='',
                                    body=traceback.format_exc())
            error_log(traceback.format_exc())
            print(traceback.format_exc())
            print('threadings = ', threading.enumerate())
            print('sleeping for {}mins ...'.format(reboot_interval/60))

            time.sleep(reboot_interval)
            tried_time += 1
            
    

    
if __name__ == '__main__':
    
    main()
        
    sys.exit(0)