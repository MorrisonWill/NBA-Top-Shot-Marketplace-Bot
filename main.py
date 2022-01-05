import asyncio
import json
import time
from typing import Optional

from account import Account
from session import Session, ResponseException
from bot import Bot, Result, Play, Moment
from asyncio import WindowsSelectorEventLoopPolicy

# lots of censored info

PROXY = 'censored'
REFRESH_NBA = 'censored'
REFRESH_DAPPER = 'censored'
CALL_NBA = 'censored'
CALL_DAPPER = 'censored'
KEY_API = 'censored'
KEY_SITE = 'censored'

ACCOUNT = 'google oauth stuff'
USERNAME = 'user'
PASSWORD = 'pass'

AUTHENTICATE = True

SET = ''
PLAYS = [
]


async def resell(bot: Bot, moment: Moment, markup: int) -> Result:
    print(f'Reselling: {moment}')
    order = await bot.create_order(moment)
    print(f'Order: {order}')
    payment = await bot.create_payment(order)
    print(f'Payment: {payment}')
    purchase = await bot.create_purchase(payment)
    print(f'Purchase: {purchase}')
    if not purchase:
        return purchase
    offer = await bot.create_offer(moment, moment.price + markup)
    print(f'Offer: {offer}')
    listing = await bot.create_listing(offer)
    print(f'Listing: {listing}')
    return listing


async def start(session: Session, refresh_nba, refresh_flow):
    bot = Bot(
        period=5,
        solve_recaptcha=await session.create_solver(key_api=KEY_API, key_site=KEY_SITE),
        call_nba=await session.create_caller(CALL_NBA, 'x-id-token', refresh_nba),
        call_flow=await session.create_caller(CALL_DAPPER, 'Authorization', refresh_flow)
    )
    plays = await bot.get_plays(batch=25)
    for play in plays:
        moments = await bot.get_moments(play)
        for moment in moments:
            print(moment)
    # while True:
    #     try:
    #         moments = []
    #
    #         async def fetch(i):
    #             results = await bot.get_moments(Play(SET, PLAYS[i]))
    #             for result in results:
    #                 moments.append(result)
    #         await asyncio.gather(*map(lambda i: fetch(i), range(0, len(DUDES) - 1)))
    #         moments.sort(key=lambda it: it[0].price)
    #         moment = moments[0]
    #         print(f'Moment: {moment}')
    #         await asyncio.sleep(10000)
    #         order = await bot.create_order(moment)
    #         print(f'Order: {order}')
    #         payment = await bot.create_payment(order)
    #         print(f'Payment: {payment}')
    #         purchase = await bot.create_purchase(payment)
    #         print(f'Purchase: {purchase}')
    #         if purchase:
    #             offer = await bot.create_offer(moment, moment.price + 1)
    #             print(f'Offer: {offer}')
    #             listing = await bot.create_listing(offer)
    #             print(f'Listing: {listing}')
    #     except ResponseException as reason:
    #         data = json.loads(str(reason))
    #         if not ('extensions' in data):
    #             raise reason
    #         error = data['extensions']
    #         if error['status_code'] != 9:
    #             raise reason
    #         message = str(error['status_message'])
    #         delay = message.split('wait ')[1].split(' minutes')[0]
    #         print(f'Waiting: {delay}m')
    #         await asyncio.sleep(int(delay) * 60)

    # order = await bot.create_order(moments[0])
    # print(f'Order: {order}')
    # payment = await bot.create_payment(order)
    # print(f'Payment: {payment}')
    # purchase = await bot.create_purchase(payment)
    # print(f'Purchase: {purchase}')

    # collection = await bot.get_collection(ACCOUNT, batch=20)
    # for owned in collection:
    #     print(owned)
    # moment = collection[0]
    # if not (moment.price == 0):
    #     raise Exception('already listed!')
    # listings = (await bot.get_moments(moment.play))[0:10]
    # print('got listings')
    # value = sum(map(lambda it: it.price, listings)) / 10
    # print(f'Value: {value}')
    # offer = await bot.create_offer(moment, value + 1)
    # print(f'Offer: {offer}')
    # listing = await bot.create_listing(offer)
    # print(f'Listing: {listing}')


async def main():
    async def no_token() -> str:
        return ''
    async with Session(PROXY) as session:
        if not AUTHENTICATE:
            return await start(session, no_token, no_token)
        async with Account(USERNAME, PASSWORD) as account:
            await start(session, account.nba_token, account.flow_token)

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
asyncio.run(main())
