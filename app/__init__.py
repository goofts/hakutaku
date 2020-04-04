# -*- coding: utf-8 -*-

"""
    GSIL
    ~~~~
    Implements Github Sensitive Information Leak

    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2018 Feei. All rights reserved
"""
import sys
import time
import gc
import random
import yaml
import traceback
import multiprocessing
from logging  import Formatter
from pathlib  import Path
from peewee   import SqliteDatabase, sqlite3
from .engine  import Engine
from .log     import logger
from .config  import Config, get_rules, tokens, daily_run_data
from .process import send_running_data_report
from playhouse.pool      import PooledDatabase
from playhouse.shortcuts import ReconnectMixin as rcmx

APP_PATH: str = str(Path(__file__).parent.parent)
STATIC_PATH: str = str(Path(APP_PATH) / Path('assets'))
CONFIG_PATH: str = str(Path(APP_PATH) / Path('conf/config.yaml'))
RULES_PATH: str = str(Path(APP_PATH)  / Path('conf/rules.yaml'))

with open(CONFIG_PATH, "r") as f:
    config = ''.join(f.readlines())
CONFIG: dict = yaml.load(config, Loader=yaml.SafeLoader)

with open(RULES_PATH, "r") as f:
    rules = ''.join(f.readlines())
RULES: dict = yaml.load(rules, Loader=yaml.SafeLoader)

del config, rules
gc.collect()

DB_PATH: str = str(Path(APP_PATH) / Path('{0}'.format(CONFIG['datase']['path'])))
DB_FILE: str = str(Path(DB_PATH) / Path('{0}.sqlite3'.format(CONFIG['datase']['name'])))

class Sqlite3Database(SqliteDatabase):
    def _connect(self):
        if sqlite3 is None:
            raise ImproperlyConfigured('SQLite driver not installed!')
        
        conn = sqlite3.connect(
            self.database,
            timeout=self._timeout,
            isolation_level=None,
            check_same_thread=False,
            **self.connect_params
        )
        
        try:
            self._add_conn_hooks(conn)
        except:
            conn.close()
            raise
        return conn

class _sqlite(PooledDatabase):
    def _is_closed(self, conn):
        try:
            conn.total_changes
        except:
            return True
        else:
            return False

class sqlite(_sqlite, Sqlite3Database):
    pass

class RetrySqliteDatabase(rcmx, sqlite):
    _instance = None

    @staticmethod
    def get_sqlite_instance():
        if not RetrySqliteDatabase._instance:
            RetrySqliteDatabase._instance = RetrySqliteDatabase(
                dbfile,
                max_connections=self.MAX_CONNECTIONS_LENGTH
            )
        return RetrySqliteDatabase._instance

DB: sqlite = RetrySqliteDatabase.get_sqlite_instance()

class Rule(object):
    def __init__(self, types=None, corp=None, keyword=None, mode='normal-match', extension=None):
        self.types = types
        self.corp = corp
        self.keyword = keyword
        self.mode = mode
        self.extension = extension

running_data = []

def search(idx, rule):
    token = random.choice(CONFIG['github']['tokens'])
    try:
        return Engine(token=token).search(rule)
    except Exception as e:
        traceback.print_exc()
        return False, None, traceback.format_exc()

def store_result(result):
    r_ret, r_rule, r_msg = result
    if r_ret:
        r_datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        if r_rule.corp.lower() in ['vulbox']:
            return
        with open(Config().run_data, 'a') as f:
            rule = '[{t}][{c}][{k}]'.format(t=r_rule.types, c=r_rule.corp, k=r_rule.keyword)
            f.write('{datetime} {ret} {rule} {msg}\r\n'.format(datetime=r_datetime, ret=r_ret, rule=rule, msg=r_msg))
        running_data.append([r_datetime, r_ret, rule, r_msg])

def start(rule_types):
    rules_objects = []
    for types, rule_list in RULES.items():
        if types in rule_types:
            for corp_name, corp_rules in rule_list.items():
                for rule_keyword, rule_attr in corp_rules.items():
                    rule_keyword = rule_keyword.strip()
                    corp_name = corp_name.strip()
                    types = types.upper()
                    if 'mode' in rule_attr:
                        mode = rule_attr['mode'].strip().lower()
                    else:
                        mode = 'normal-match'
                    if 'ext' in rule_attr:
                        extension = rule_attr['ext'].strip()
                    else:
                        extension = None
                    r = Rule(types, corp_name, rule_keyword, mode, extension)
                    rules_objects.append(r)
    if len(rules_objects) == 0:
        logger.critical('get rules failed, rule types not found!')
        exit(0)
    logger.info('rules length: {rl}'.format(rl=len(rules_objects)))
    pool = multiprocessing.Pool()
    for idx, rule_object in enumerate(rules_objects):
        logger.info('>>>>>>>>>>>>> {n} > {r} >>>>>>'.format(n=rule_object.corp, r=rule_object.keyword))
        pool.apply_async(search, args=(idx, rule_object), callback=store_result)
    pool.close()
    pool.join()

def generate_report(data):
    for rd in data:
        datetime, ret, rule, msg = rd
        html = '<li> {datetime} {ret} {rule} {msg}</li>'.format(datetime=datetime, ret=ret, rule=rule, msg=msg)
        run_data = daily_run_data()
        run_data['list'].append(html)
        if ret:
            run_data['found_count'] += msg
            run_data['job_success'] += 1
        else:
            run_data['job_failed'] += 1
        daily_run_data(run_data)

def gsil():
    if sys.argv[1] == '--report':
        send_running_data_report()
    elif sys.argv[1] == '--verify-tokens':
        for i, token in enumerate(tokens):
            ret, msg = Engine(token=token).verify()
            logger.info('{i} {ret} token: {token} {msg}'.format(i=i, msg=msg, token=token, ret=ret))
    else:
        logger.info('start monitor github information leakage: {types}'.format(types=sys.argv[1]))
        start(sys.argv[1])
        generate_report(running_data)

if __name__ == '__main__':
    gsil()
