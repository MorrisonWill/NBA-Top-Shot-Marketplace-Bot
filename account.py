import asyncio
from pyppeteer.launcher import Launcher, launch


class Account:
    def __init__(self, username: str, password: str, secret: str = None):
        self.username = username
        self.password = password
        self.secret = secret
        # if proxy is None:
        #     arguments = []
        #     self.proxy = None
        # else:
        #     parsed = urlparse(proxy)
        #     arguments = [f'--proxy-server={parsed.hostname}:{parsed.port}']
        #     self.proxy = {'username': parsed.username, 'password': parsed.password}
        self.launcher = Launcher(ignoreDefaultArgs=True)

    async def __aenter__(self):
        self.browser = await self.launcher.launch()
        page = (await self.browser.pages())[0]
        await page.goto('censored')
        login = await page.waitFor('svg[viewBox="0 0 202 44"]')
        await login.asElement().click()
        first = (await page.waitFor('input[type="email"]')).asElement()
        await first.type(self.username)
        await first.press('Enter')
        second = (await page.waitFor('input[type="password"]')).asElement()
        await asyncio.sleep(2)
        await second.type(self.password)
        await second.press('Enter')
        await page.waitFor('a[href="/"]')
        await page.goto('https://accounts.meetdapper.com')
        self.flow = await self.browser.newPage()
        self.nba = await self.browser.newPage()
        await self.flow.goto('censored')
        await self.nba.goto('censored')
        await page.close()
        return self

    async def nba_token(self):
        response = await self.nba.reload()
        return (await response.json())['idToken']

    async def flow_token(self):
        response = await self.flow.reload()
        return (await response.json())['accessToken']

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        for page in await self.browser.pages():
            await page.close()
        await self.browser.close()
