import asyncio
import json
from typing import List
from typing import Callable
from typing import Awaitable
from time import time
from enum import Enum

from session import ResponseException

GET_MOMENTS = """
query GetUserMomentListingsDedicated($set_id: ID!, $play_id: ID!) {
    getUserMomentListings(input: {
        setID: $set_id
        playID: $play_id
    }) {
        data {
            momentListings {
                moment {
                    id
                    price
                    flowId
                    owner { dapperID }
                }
            }
      }
    }
}
"""
GET_PLAYS = """
query SearchMomentListingsDefault($limit: Int!, $cursor: Cursor!) {
    searchMomentListings(
        input: {
            filters: {}
            sortBy: PRICE_USD_ASC
            searchInput: {
                pagination: {
                    cursor: $cursor,
                    limit: $limit,
                    direction: RIGHT
                }
            }
        }
    ) {
        data {
            searchSummary {
                pagination { rightCursor }
                data {
                    ... on MomentListings {
                        size
                        data {
                            ... on MomentListing {
                                set { id }
                                play { id }
                                priceRange {
                                    min
                                    max
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""
GET_COLLECTION = """
query SearchMintedMoments($owner: String!, $limit: Int!, $cursor: Cursor!) {
    searchMintedMoments(input: {
        sortBy: ACQUIRED_AT_DESC,
        filters: { byOwnerDapperID: [$owner] },
        searchInput: {
            pagination: {
                cursor: $cursor,
                limit: $limit,
                direction: RIGHT
            }
        }
    }) {
        data {
            searchSummary {
                count { count }
                pagination { rightCursor }
                data {
                    ... on MintedMoments {
                        size
                        data {
                            id
                            price
                            flowId
                            set { id }
                            play { id }
                        }
                    }
                }
            }
        }
    }
}
"""
CREATE_ORDER = """
mutation PurchaseP2PMomentMutation(
    $moment_id: String!, $flow_id: String!, $price: Price!, $seller_id: String!, $token: String!
) {
    purchaseP2PMoment(input: {
        momentID: $moment_id
        momentFlowID: $flow_id
        price: $price
        sellerID: $seller_id
        recaptchaToken: $token
        momentName: " "
        momentDescription: " "
        redirectURL: " "
    }) { orderID }
}
"""
CREATE_OFFER = """
mutation CreateMomentSaleMutation($moment_id: String!, $flow_id: String!, $price: Price!) {
    createMomentSale(input: {
        momentID: $moment_id
        momentFlowID: $flow_id
        price: $price
        redirectURL: " "
    }) { orderID }
}
"""
CHECK_OFFER = """
query GetUserP2PListingOrder($offer_id: String!) {
    getUserP2PListingOrder(input: {
        orderID: $offer_id
    }) {
        data {
            status
            state
            listingInvocationIntentID
        }
    }
}
"""
CHECK_ORDER = """
query GetUserP2PPurchaseOrder($order_id: String!) {
    getUserP2PPurchaseOrder(input: {
        orderID: $order_id
    }) {
        data {
            state
            status
            purchaseIntentID
        }
    }
}
"""
CREATE_LISTING = """
mutation ConfirmInvocation($intent_id: ID!) {
 confirmInvocation(input: {
    id: $intent_id
 })
}
"""
CREATE_PAYMENT = """
query GetPurchase($intent_id: ID!) {
    getPurchase(input: {
        requestID: $intent_id
    }) {
        paymentOptions {
            id
            amount
            paymentType
        }
    }
}
"""
CREATE_PURCHASE = """
mutation ConfirmPurchase($intent_id: ID!, $payment_id: ID!) {
    confirmPurchase(input: {
        requestID: $intent_id
        selectedOptionID: $payment_id
    }) { status }
}
"""


class Play:
    def __init__(self, set_id: str, play_id: str, price: int = 0):
        self.set_id = set_id
        self.play_id = play_id
        self.price = price

    def __str__(self):
        return f'${self.price} - {self.set_id} - {self.play_id}'


class Moment:
    def __init__(self, play: Play, moment_id: str, flow_id: str, owner_id: str, price: int):
        self.play = play
        self.moment_id = moment_id
        self.flow_id = flow_id
        self.owner_id = owner_id
        self.price = price

    def __str__(self):
        return f'${self.price} - {self.moment_id}'

    def __eq__(self, other):
        return self.moment_id == other.moment_id


class Order:
    def __init__(self, order_id: str, intent_id: str):
        self.order_id = order_id
        self.intent_id = intent_id

    def __str__(self):
        return f'{self.order_id} - {self.intent_id}'


class Payment:
    def __init__(self, order: Order, payment_id: str):
        self.order = order
        self.payment_id = payment_id

    def __str__(self):
        return f'({self.order}) - {self.payment_id}'


class Offer:
    def __init__(self, offer_id: str, intent_id: str):
        self.offer_id = offer_id
        self.intent_id = intent_id

    def __str__(self):
        return f'{self.offer_id} - {self.intent_id}'


class Result(Enum):
    SUCCESSFUL = 1
    FAILED = 2

    def __bool__(self) -> bool:
        return self == Result.SUCCESSFUL


class Bot:
    def __init__(
        self, period: int,
        solve_recaptcha: Callable[[str], Awaitable[str]],
        call_nba: Callable[[str, dict], Awaitable[dict]],
        call_flow: Callable[[str, dict], Awaitable[dict]]
    ):
        self.period = period
        self.solve_recaptcha = solve_recaptcha
        self.call_nba = call_nba
        self.call_flow = call_flow

    async def get_plays(self, batch: int = 75, cap: int = 100000) -> List[Play]:
        plays = []
        cursor = ['']
        while True:
            try:
                data = (await self.call_nba(GET_PLAYS, {
                    'limit': batch,
                    'cursor': cursor[0]
                }))['data']['searchSummary']
                size = data['data']['size']
                for play in data['data']['data']:
                    if len(plays) < cap:
                        plays.append(Play(
                            set_id=play['set']['id'],
                            play_id=play['play']['id'],
                            price=int(float(play['priceRange']['min']))
                        ))
                if size < batch or len(plays) >= cap:
                    break
                cursor[0] = data['pagination']['rightCursor']
            except Exception as e:
                print('trying again')
                print(e)
                await asyncio.sleep(2)
        plays.sort(key=lambda it: it.price)
        return plays

    async def get_moments(self, play: Play) -> List[Moment]:
        response = await self.call_nba(GET_MOMENTS, {
            'set_id': play.set_id, 'play_id': play.play_id
        })
        if response is None:
            return []
        moments = response['data']['momentListings']
        return list(map(lambda it: Moment(
            play=play, moment_id=it['moment']['id'],
            flow_id=it['moment']['flowId'],
            owner_id=it['moment']['owner']['dapperID'],
            price=int(float(it['moment']['price']))
        ), moments))

    async def get_collection(self, owner_id: str, batch: int, cap: int = 1000000) -> List[Moment]:
        moments = []
        cursor = ['']
        while True:
            try:
                data = (await self.call_nba(GET_COLLECTION, {
                    'owner': owner_id, 'limit': batch, 'cursor': cursor[0]
                }))['data']['searchSummary']
                for moment in data['data']['data']:
                    if len(moments) < cap:
                        moments.append(Moment(
                            play=Play(
                                set_id=moment['set']['id'],
                                play_id=moment['play']['id'],
                            ),
                            moment_id=moment['id'],
                            flow_id=moment['flowId'],
                            owner_id=owner_id,
                            price=int(float(moment['price']))
                        ))
                size = data['data']['size']
                if size < batch or len(moments) >= cap:
                    break
                cursor[0] = data['pagination']['rightCursor']
            except Exception as e:
                print(e)
                await asyncio.sleep(2)
        return moments

    async def create_order(self, moment: Moment) -> Order:
        url = 'https://www.nbatopshot.com/listings/p2p/{}+{}'
        token = await self.solve_recaptcha(
            url.format(moment.play.play_id, moment.play.play_id)
        )
        order_id = (await self.call_nba(CREATE_ORDER, {
            'moment_id': moment.moment_id,
            'flow_id': moment.flow_id,
            'seller_id': moment.owner_id,
            'price': str(moment.price),
            'token': token,
        }))['orderID']
        print(order_id)
        # order_id = 'f186faa7-5e73-407b-87ec-58533157d814'
        while True:
            try:
                response = await self.call_nba(CHECK_ORDER, {'order_id': order_id})
                state = response['data']['state']
                print(json.dumps(response, indent=3))
                if state == 'CREATE_INTENT_SUCCEEDED':
                    return Order(order_id, response['data']['purchaseIntentID'])
                elif state == 'PURCHASE_FAILED':
                    raise Exception('Purchase failed!')
                await asyncio.sleep(self.period)
            except ResponseException:
                pass

    async def create_payment(self, order: Order) -> Payment:
        response = self.call_flow(CREATE_PAYMENT, {'intent_id': order.intent_id})
        payments = (await response)['paymentOptions']
        payment = [it for it in payments if it['paymentType'] == 'DAPPER_CREDITS'][0]
        balance = await self.call_flow('query getBalance() { getBalance() }', {})
        if payment['amount'] <= balance:
            return Payment(order, payment['id'])
        raise Exception('Out of Dapper credits!')

    async def create_purchase(self, payment: Payment) -> Result:
        while True:
            try:
                if not (await self.call_flow(CREATE_PURCHASE, {
                    'intent_id': payment.order.intent_id,
                    'payment_id': payment.payment_id
                }))['status'] == 'INITIATED':
                    raise Exception('Failed to get moment!')
                break
            except ResponseException as reason:
                print(reason)
                await asyncio.sleep(self.period)
        while True:
            try:
                data = await self.call_nba(CHECK_ORDER, {
                    'order_id': payment.order.order_id
                })
                status = data['data']['status']
                if status == 'FAILED':
                    return Result.FAILED
                elif status == 'SUCCEEDED':
                    return Result.SUCCESSFUL
            except Exception as e:
                print(f'error: {e}')
            await asyncio.sleep(self.period)

    async def create_offer(self, moment: Moment, price: int) -> Offer:
        try:
            offer_id = (await self.call_nba(CREATE_OFFER, {
                'moment_id': moment.moment_id,
                'flow_id': moment.flow_id,
                'price': str(price)
            }))['orderID']
            while True:
                try:
                    response = await self.call_nba(CHECK_OFFER, {'offer_id': offer_id})
                    if response['data']['state'] == 'LISTING_INVOCATION_INTENT_CREATED':
                        return Offer(offer_id, response['data']['listingInvocationIntentID'])
                except ResponseException:
                    pass
                await asyncio.sleep(self.period)
        except ResponseException as reason:
            data = json.loads(str(reason))
            if not ('extensions' in data):
                raise reason
            error = data['extensions']
            if error['status_code'] != 9:
                raise reason
            message = str(error['status_message'])
            delay = message.split('wait ')[1].split(' minutes')[0]
            print(f'Waiting: {delay}m')
            await asyncio.sleep(int(delay) * 60)
            return await self.create_offer(moment, price)

    async def create_listing(self, offer: Offer):
        listing = await self.call_flow(CREATE_LISTING, {
            'intent_id': offer.intent_id,
        })
        print(listing)
        if not listing == offer.intent_id:
            return Result.FAILED
        while True:
            try:
                response = await self.call_nba(CHECK_OFFER, {'offer_id': offer.offer_id})
                print(response['data']['state'])
                if response['data']['state'] == 'LISTING_SUCCEEDED':
                    return Result.SUCCESSFUL
            except ResponseException as e:
                print('error')
                print(e)
                pass
            await asyncio.sleep(self.period)

