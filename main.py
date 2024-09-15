import asyncio
import execjs
from functools import partialmethod
from aiohttp import ClientResponseError
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.eth import AsyncEth
from web3.net import AsyncNet
from aiohttp.client import ClientSession
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from loguru import logger

with open('encrypt.js') as f:
    js_code = f.read()


def get_data(address: str, project_id: str = None, voting_power: str = None):
    js = execjs.compile(js_code)
    return js.call('get_data', address, project_id, voting_power)


class MorphL2:
    URL = 'https://events-api-holesky.morphl2.io/activities'

    def __init__(self, proxy: str, private: str):
        proxy = Proxy.from_str(proxy).as_url
        self.session = ClientSession(connector=ProxyConnector.from_url(proxy))
        self.client = AsyncWeb3(
            AsyncHTTPProvider('https://rpc-holesky.morphl2.io', request_kwargs={'proxy': proxy}),
            modules={'eth': (AsyncEth,), 'net': (AsyncNet,)}
        )
        self.account = Account.from_key(private)

    def _get_signature(self):
        account: LocalAccount = self.account
        text = 'Welcome to Morph!\n\nThis is only for address check purposes, it will not trigger a blockchain transaction or cost any gas fees.\n'
        return '0x' + account.sign_message(encode_defunct(text=text)).signature.hex()

    async def request(self, method: str, path: str, **kwargs):
        for i in range(5):
            try:
                response = await self.session.request(
                    method, f'{self.URL}/{path}', **kwargs
                )
                response.raise_for_status()
                break
            except ClientResponseError as e:
                logger.warning(f'{self.account.address} | {e}. {i + 1}) Trying again in 5 seconds')
                await asyncio.sleep(5)
        else:
            logger.error(f'{self.account.address} | Couldn\'t do anything. Giving up.')
            return
        data = await response.json()
        if data['code'] == 1000:
            return data.get('data', {})
        else:
            logger.warning(f'{self.account.address} | {data["message"]}')

    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")

    async def start(self):
        funcs = [self.sign_in(), self.open_blind_box(), self.info()]
        for f in funcs:
            await f
            await asyncio.sleep(3)
        await self.session.close()

    async def sign_in(self):
        signature = self._get_signature()
        data, message = get_data(self.account.address)
        res = await self.post('sign_in', json={'signature': signature, 'data': data, 'message': message})
        if res is not None:
            logger.success(f'{self.account.address} | Daily check-in')

    async def open_blind_box(self):
        signature = self._get_signature()
        data, message = get_data(self.account.address)
        res = await self.post('open_blind_box', json={'signature': signature, 'data': data, 'message': message})
        if res is not None:
            logger.success(f'{self.account.address} | Got {res["blindBoxValue"]} VP from box')

    async def info(self):
        res = await self.get('personal_stats', params={'address': self.account.address})
        if res is not None:
            logger.success(f'{self.account.address} | Total VP: {res["total_voting_power"]}')


def read_file(filename: str) -> list[str]:
    with open(filename, 'r') as f:
        return [line.strip() for line in f.readlines()]


async def main():
    proxies = read_file('proxies.txt')
    privates = read_file('source.txt')
    await asyncio.gather(
        *[MorphL2(private=private, proxy=proxy).start() for proxy, private in list(zip(proxies, privates))])


if __name__ == '__main__':
    asyncio.run(main())
