import asyncio
import json
import time
from typing import Callable, Awaitable

from aiohttp import ClientSession, ContentTypeError
from pyppeteer.launcher import Launcher
import os


class ResponseException(Exception):
    pass

class Session:
    def __init__(self, proxy: str):
        self.launcher = Launcher(ignoreDefaultArgs=True)
        self.proxy = proxy
        self.calls = 0
        self.errors = 0
        self.flared = 0
        self.last = time.time()

    async def __aenter__(self):
        os.environ.setdefault('HTTP_PROXY', self.proxy)
        os.environ.setdefault('HTTPS_PROXY', self.proxy)
        self.http = ClientSession(trust_env=True)
        os.environ.pop('HTTP_PROXY')
        os.environ.pop('HTTPS_PROXY')
        return self

    async def create_caller(
        self, url: str, key: str,
        refresh: Callable[[], Awaitable[str]],
    ) -> Callable[[str, dict], Awaitable[dict]]:
        duration = 600
        update = [0]
        token = ['']

        async def call(query: str, variables: dict) -> dict:
            name = query.split('(', 1)[0].split(' ', 1)[1]
            method = query.split('(', 2)[1].split('{')[1].lstrip()
            if update[0] < time.time():
                token[0] = await refresh()
                update[0] = int(time.time()) + duration
            headers = {
                key: token[0],
                'content-type': 'application/json'
            }
            body = {
                'operationName': name,
                'variables': variables,
                'query': query
            }
            try:
                # TODO move this stuff into bot or main.
                self.calls += 1
                lag = self.last - time.time()
                if lag <= 0:
                    self.last = time.time() + 10
                    rate = 100 * float(self.errors + self.flared) / self.calls
                    print(f'(({self.errors}, {self.flared}) / {self.calls}) - {rate:.2f}% - {abs(lag):.1f}s')
                async with self.http.post(url=url, headers=headers, json=body) as response:
                    data = await response.json()
                    if 'error' in data:
                        raise ResponseException(json.dumps(data['error'], indent=3))
                    elif 'errors' in data:
                        for error in data['errors']:
                            raise ResponseException(json.dumps(error, indent=3))
                    elif ('data' in data) and (method in data['data']):
                        return data['data'][method]
                    else:
                        raise ResponseException(json.dumps(data, indent=3))
            except ResponseException as reason:
                raise reason
            except ContentTypeError:
                self.flared += 1
                return await call(query, variables)
            except Exception as e:
                print(f'Reason: {e}')
                self.errors += 1
                return await call(query, variables)
        return call

    async def create_solver(self, key_api: str, key_site: str) -> Callable[[str], Awaitable[str]]:
        async def solve(url: str):
            params = {
                'key': key_api,
                'method': 'userrecaptcha',
                'action': 'verify',
                'version': 'v3',
                'googlekey': key_site,
                'pageurl': url,
                'json': '1'
            }
            try:
                async with self.http.get('http://CAPTCHA SOLVER.com/in.php', params=params) as response:
                    token = (await response.json())['request']
                    while True:
                        data = {'key': key_api, 'action': 'get', 'json': '1', 'id': token}
                        async with self.http.get('http://2captcha.com/res.php', params=data) as check:
                            data = await check.json()
                            if data['status'] == 1:
                                return data['request']
                        await asyncio.sleep(15)
            except Exception as reason:
                print(f'Reason: {reason}')
        return solve

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.http.close()
