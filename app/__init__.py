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
from pathlib import Path

APP_PATH: str = str(Path(__file__).parent.parent)
STATIC_PATH: str = str(Path(APP_PATH) / Path('assets'))
CONFIG_PATH: str = str(Path(APP_PATH) / Path('conf/config.yaml'))
RULES_PATH: str = str(Path(APP_PATH)  / Path('conf/rules.yaml'))
DB_FILE: str = str(Path(APP_PATH) / Path('db/{0}.sqlite3'.format('dev')))

class Rule(object):
    def __init__(self, types=None, corp=None, keyword=None, mode='normal-match', extension=None, lines=5):
        self.types = types
        self.corp = corp
        self.keyword = keyword
        self.mode = mode
        self.extension = extension
        self.lines = lines

def store_result(result):
    r_ret, r_rule, r_msg = result
    if r_ret:
        r_datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        if r_rule.corp.lower() in ['vulbox']:
            return

# 搜索源码
from app.engine import Engine
def search(index, rule):
    with open(CONFIG_PATH, "r") as f:
        CONFIG: dict = yaml.load(''.join(f.readlines()), Loader=yaml.SafeLoader)
    users = random.choice(CONFIG['github']['users'])
    for key in users:
        user = users[key]
    try:
        return Engine(user=user, pages=CONFIG['pages'], mail=CONFIG['mail'], repo=CONFIG['repo'], codes=CONFIG['codes']).search(rule)
    except Exception as e:
        traceback.print_exc()
        return False, None, traceback.format_exc()

# 获取搜索规则,并开启搜索进程
def start():
    with open(RULES_PATH, "r") as f:
        RULES: dict = yaml.load(''.join(f.readlines()), Loader=yaml.SafeLoader)
    print (RULES)
    rules_objects = []
    for types, rule_list in RULES.items():
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
                    extension = 'php,java'
                if 'line' in rule_attr:
                    lines = rule_attr['line']
                else:
                    lines = 5
                rule = Rule(types, corp_name, rule_keyword, mode, extension, lines)
                rules_objects.append(rule)
    pool = multiprocessing.Pool()
    for index, rule_object in enumerate(rules_objects):
        time.sleep(1)
        pool.apply_async(search, args=(index, rule_object), callback=store_result)
    pool.close()
    pool.join()
