from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Position(BaseModel):
    ticker: str
    quantity: float
    averagePrice: float
    currentPrice: float
    ppl: float
    fxPpl: Optional[float] = None
    initialFillDate: str
    frontend: str = "IOS"
    maxBuy: Optional[float] = None
    maxSell: Optional[float] = None
    pieQuantity: float = 0


class Cash(BaseModel):
    availableToTrade: float
    reservedForOrders: float = 0
    inPies: float = 0


class Investments(BaseModel):
    currentValue: float
    totalCost: float
    realizedProfitLoss: float
    unrealizedProfitLoss: float


class AccountSummary(BaseModel):
    id: int
    currency: str
    totalValue: float
    cash: Cash
    investments: Investments


class Instrument(BaseModel):
    ticker: str
    name: str
    isin: str
    currency: str


class Tax(BaseModel):
    name: str
    quantity: float
    currency: str
    chargedAt: str


class WalletImpact(BaseModel):
    currency: str
    netValue: float
    fxRate: float
    taxes: list[Tax] = []


class OrderDetail(BaseModel):
    id: int
    strategy: str
    type: str
    ticker: str
    status: str
    value: float
    filledValue: float
    currency: str
    extendedHours: bool = False
    initiatedFrom: str = "IOS"
    side: str
    createdAt: str
    instrument: Instrument


class Fill(BaseModel):
    id: int
    quantity: float
    price: float
    type: str
    tradingMethod: str
    filledAt: str
    walletImpact: WalletImpact


class Order(BaseModel):
    order: OrderDetail
    fill: Fill


class Dividend(BaseModel):
    ticker: str
    instrument: Instrument
    reference: str
    quantity: float
    amount: float
    currency: str
    grossAmountPerShare: float
    amountInEuro: float
    paidOn: str
    type: str = "DIVIDEND"


class Transaction(BaseModel):
    type: str
    amount: float
    currency: str
    reference: str
    dateTime: str
