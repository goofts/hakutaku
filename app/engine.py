# -*- coding: utf-8 -*-

"""
    engine
    ~~~~~~
    Implements Github search engine

    :license:   GPL, see LICENSE for more details.
    :copyright: Copyright (c) 2018 Feei. All rights reserved
"""
import re
import time
import json
import hashlib
import socket
import traceback
import requests
from github import Github, GithubException
from bs4    import BeautifulSoup
from IPy    import IP
from tld    import get_tld
from app.orm import DB, repository, hashlist

if not repository.table_exists():
    repository.create_table()
    hashlist.create_table()

regex_mail = r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
regex_host = r"@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
regex_pass = r"(pass|password|pwd)"
regex_title = r"<title>(.*)<\/title>"
regex_ip = r"^((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}$"
regex_url = '(https://github.com/[a-zA-Z0-9_.+-]+/[a-zA-Z0-9_.+-]+)/\w+'

class Engine(object):
    def __init__(self, user, pages, mail, repo, codes):
        self.pages = pages
        self.mail  = mail
        self.repo  = repo
        self.codes = codes
        self.per_page = int(1000/pages)
        self.g = Github(user["name"], user["passwd"], per_page=self.per_page)
        self.result = None
        self.exclude_result = None
        self.rule_object = None

        self.code = ''
        self.name = ''
        self.sha = ''
        self.url = ''
        self.path = ''

#     对关键词代码进行范围截取
    def match_codes(self):
        codes = self.code.replace('<img', '').splitlines()
        codes_len = len(codes)
        keywords = self._keywords()
        if self.rule_object.mode == 'mail':
            return self._mail(codes)
        if self.rule_object.mode == 'only-match':
            return codes
        if self.rule_object.mode == 'normal-match':
            match_codes = []
            for idx, code in enumerate(codes):
                for keyword in keywords:
                    if keyword in code:
                        idxs = []
                        for i in range(-1*self.rule_object.lines, -0):
                            i_idx = idx + i
                            if i_idx in idxs:
                                continue
                            
                            if i_idx < 0:
                                continue
                            
                            if codes[i_idx].strip() == '':
                                continue
                            
                            idxs.append(i_idx)
                            match_codes.append(codes[i_idx])
                        
                        if idx not in idxs:
                            match_codes.append(codes[idx])
                        
                        for i in range(1, self.rule_object.lines+1):
                            i_idx = idx + i
                            if i_idx in idxs:
                                continue
                            if i_idx >= codes_len:
                                continue
                            if codes[i_idx].strip() == '':
                                continue

                            idxs.append(i_idx)
                            match_codes.append(codes[i_idx])
            return match_codes
        return []

#     去除仓库常规误报
    def _exclude_repository(self):
        ret = False
        full_path = '{repository}/{path}'.format(repository=self.name.lower(), path=self.path.lower())
        for err in self.repo:
            if re.search(err, full_path) is not None:
                return True
        return ret

#     去除代码常规误报
    def _exclude_codes(self):
        ret = False
        for ecr in self.codes:
            if re.search(ecr, '\n'.join(self.code)) is not None:
                return True
        return ret

#     按页对结果进行处理
    def process_pages(self, pages_content, page, total):
        time.sleep(0.1)
        rate_limiting = self.g.rate_limiting
        rate_limiting_reset_time = self.g.rate_limiting_resettime
        for index, content in enumerate(pages_content):
            current_i = page * self.per_page + index
            time.sleep(0.1)
            try:
                time.sleep(0.01)
                self.url  = content.html_url.strip()
                time.sleep(0.01)
                self.sha  = content.sha.strip()
                time.sleep(0.01)
                self.path = content.path.strip()
                time.sleep(0.01)
                self.name = content.repository.full_name.strip()
                time.sleep(0.01)
                self.code = content.decoded_content.decode('utf-8')
            except Exception as e:
                continue

#             对相同文件进行去重
            with DB.connection_context():
                try:
                    hashlist.insert({'unique':self.sha}).execute()
                except Exception as e:
                    continue

            self.code = self.match_codes()
            if len(self.code) == 0:
                continue

            result = {
                'url': self.url,
                'match_codes': self.code,
                'hash': self.sha,
                'code': self.code,
                'repository': self.name,
                'path': self.path,
            }
            
            print (result)

            if self._exclude_repository():
                continue

            if self._exclude_codes():
                self.exclude_result[current_i] = result
            else:
                self.result[current_i] = result

        return True

#     检验用户账号可用性
    def verify(self):
        try:
            ret = self.g.rate_limiting
            return True, 'TOKEN-PASSED: {r}'.format(r=ret)
        except GithubException as e:
            return False, 'TOKEN-FAILED: {r}'.format(r=e)

#     搜索进程主体
    def search(self, rule_object):
        self.rule_object = rule_object
        if self.rule_object.extension is not None:
            for ext in self.rule_object.extension.split(','):
                try:
                    time.sleep(0.1)
                    rate_limiting = self.g.rate_limiting
                    rate_limiting_reset_time = self.g.rate_limiting_resettime
                    ext_query = 'extension:{ext} '.format(ext=ext.strip().lower())
                    keyword = '{keyword} {ext}'.format(keyword=self.rule_object.keyword, ext=ext_query)
                    time.sleep(0.1)
                    resource = self.g.search_code(keyword, sort="indexed", order="desc")
                    total = resource.totalCount
                except GithubException as e:
                    return False, self.rule_object, msg

                print (total)
                if total < self.per_page:
                    pages = 1
                elif total > 1000:
                    pages = self.pages
                else:
                    pages = int(total/self.per_page)
                for page in range(pages):
                    self.result = {}
                    self.exclude_result = {}
                    time.sleep(0.1)
                    try:
                        pages_content = resource.get_page(page)
                    except socket.timeout:
                        continue
                    except GithubException as e:
                        return False, self.rule_object, msg

                    print (pages_content)
                    if not self.process_pages(pages_content, page, total):
                        break

                    for key, value in self.result.items():
                        unique = json.dumps({'url':re.findall(regex_url, value['url'])[0], 'keyword':self.rule_object.corp}).encode('utf-8')
                        data = {
                            'unique':hashlib.md5(unique).hexdigest()
                            ,'url':re.findall(regex_url, value['url'])[0]
                            ,'name':self.rule_object.corp
                            ,'keyword':self.rule_object.keyword
                            ,'count':value['match_codes']
                        }
                        with DB.connection_context():
                            repository.insert(data).on_conflict_ignore().execute()

        return True, self.rule_object, len(self.result)

#     分割关键词
    def _keywords(self):
        if '"' not in self.rule_object.keyword and ' ' in self.rule_object.keyword:
            return self.rule_object.keyword.split(' ')
        else:
            if '"' in self.rule_object.keyword:
                return [self.rule_object.keyword.replace('"', '')]
            else:
                return [self.rule_object.keyword]

    def _mail(self, codes):
        match_codes = []
        mails = []
#         找到所有邮箱地址
        mail_multi = re.findall(regex_mail, codes)
        for mm in mail_multi:
            mail = mm.strip().lower()
            if mail in mails:
                continue
            
            host = re.findall(regex_host, mail)
            host = host[0].strip()
            if host in self.mail:
                continue
            
            mails.append(mail)

            # get mail host's title
            is_inner_ip = False
            if re.match(regex_ip, host) is None:
                try:
                    top_domain = get_tld(host, fix_protocol=True)
                except Exception as e:
                    top_domain = host
                
                if top_domain == host:
                    domain = 'http://www.{host}'.format(host=host)
                else:
                    domain = 'http://{host}'.format(host=host)
            else:
                if IP(host).iptype() == 'PRIVATE':
                    is_inner_ip = True
                domain = 'http://{host}'.format(host=host)
            title = '<Unknown>'
            if is_inner_ip is False:
                try:
                    response = requests.get(domain, timeout=4).content
                except Exception as e:
                    title = '<{msg}>'.format(msg=e)
                else:
                    try:
                        soup = BeautifulSoup(response, "html5lib")
                        if hasattr(soup.title, 'string'):
                            title = soup.title.string.strip()[0:150]
                    except Exception as e:
                        title = 'Exception'
                        traceback.print_exc()

            else:
                title = '<Inner IP>'

            match_codes.append("{mail} {domain} {title}".format(mail=mail, domain=domain, title=title))
        return match_codes
