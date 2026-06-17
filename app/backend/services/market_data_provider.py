"""Unified market data provider with Yahoo Finance primary and FinancialDatasets.ai fallback.

Architecture:
  YahooFinanceProvider (primary)  →  free, ETFs work (SPY/QQQ/VOO)
  FinancialDatasetsProvider (fallback)  →  paid API, richer data
  MarketDataProvider (orchestrator)  →  try primary → fallback on failure

Usage:
  from app.backend.services.market_data_provider import get_prices
  prices = get_prices("SPY", "2025-01-01", "2025-06-01")
"""

import datetime
import logging
import os
from typing import Optional

import pandas as pd
import yfinance as yf

from src.data.models import (
    CompanyNews,
    FinancialMetrics,
    InsiderTrade,
    LineItem,
    Price,
)
from src.tools import api as fd_api

logger = logging.getLogger(__name__)

_PRICE_CACHE: dict[str, list[Price]] = {}
_METRICS_CACHE: dict[str, list[FinancialMetrics]] = {}
_NEWS_CACHE: dict[str, list[CompanyNews]] = {}


def _log(ticker: str, provider: str, status: str, detail: str = ""):
    msg = f"  [DATA_PROVIDER] ticker={ticker} provider={provider} status={status}"
    if detail:
        msg += f" {detail}"
    print(msg)


# ──────────────────────────────────────────────
#  Provider: Yahoo Finance
# ──────────────────────────────────────────────

class YahooFinanceProvider:

    @staticmethod
    def get_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
        try:
            yft = yf.Ticker(ticker)
            df = yft.history(start=start_date, end=end_date)
            if df.empty:
                _log(ticker, "yahoo", "empty", "no price data returned")
                return []
            prices = []
            for idx, row in df.iterrows():
                prices.append(Price(
                    open=float(row["Open"]),
                    close=float(row["Close"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    volume=int(row["Volume"]),
                    time=str(idx.date()),
                ))
            _log(ticker, "yahoo", "success", f"prices={len(prices)}")
            return prices
        except Exception as e:
            _log(ticker, "yahoo", "error", str(e)[:120])
            return []

    @staticmethod
    def get_financial_metrics(ticker: str) -> list[FinancialMetrics]:
        try:
            yft = yf.Ticker(ticker)
            info = yft.info
            if not info or not info.get("marketCap"):
                _log(ticker, "yahoo", "empty", "no info data")
                return []
            fm = FinancialMetrics(
                ticker=ticker,
                report_period=datetime.date.today().isoformat(),
                period="ttm",
                currency=info.get("currency", "USD"),
                market_cap=info.get("marketCap"),
                enterprise_value=info.get("enterpriseValue"),
                price_to_earnings_ratio=info.get("trailingPE"),
                price_to_book_ratio=info.get("priceToBook"),
                price_to_sales_ratio=info.get("priceToSalesTrailing12Months"),
                enterprise_value_to_ebitda_ratio=info.get("enterpriseToEbitda"),
                enterprise_value_to_revenue_ratio=info.get("enterpriseToRevenue"),
                free_cash_flow_yield=None,
                peg_ratio=info.get("pegRatio"),
                gross_margin=info.get("grossMargins"),
                operating_margin=info.get("operatingMargins"),
                net_margin=info.get("profitMargins"),
                return_on_equity=info.get("returnOnEquity"),
                return_on_assets=info.get("returnOnAssets"),
                return_on_invested_capital=None,
                asset_turnover=info.get("assetTurnover"),
                inventory_turnover=None,
                receivables_turnover=None,
                days_sales_outstanding=None,
                operating_cycle=None,
                working_capital_turnover=None,
                current_ratio=info.get("currentRatio"),
                quick_ratio=info.get("quickRatio"),
                cash_ratio=None,
                operating_cash_flow_ratio=None,
                debt_to_equity=info.get("debtToEquity"),
                debt_to_assets=None,
                interest_coverage=None,
                revenue_growth=info.get("revenueGrowth"),
                earnings_growth=info.get("earningsGrowth"),
                book_value_growth=None,
                earnings_per_share_growth=None,
                free_cash_flow_growth=None,
                operating_income_growth=None,
                ebitda_growth=None,
                payout_ratio=info.get("payoutRatio"),
                earnings_per_share=info.get("trailingEps"),
                book_value_per_share=info.get("bookValue"),
                free_cash_flow_per_share=None,
            )
            _log(ticker, "yahoo", "success", "financial_metrics=1")
            return [fm]
        except Exception as e:
            _log(ticker, "yahoo", "error", f"metrics: {str(e)[:120]}")
            return []

    @staticmethod
    def get_company_news(ticker: str, limit: int = 100) -> list[CompanyNews]:
        try:
            yft = yf.Ticker(ticker)
            news = yft.news
            if not news:
                _log(ticker, "yahoo", "empty", "no news")
                return []
            results = []
            for article in news[:limit]:
                content = article.get("content", {}) if isinstance(article, dict) else article
                if isinstance(content, dict):
                    title = content.get("title", "")
                    source = content.get("publisher", "Yahoo Finance")
                    url = content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else content.get("url", "")
                    date_str = content.get("pubDate", "")
                else:
                    title = getattr(content, "title", str(content)) if hasattr(content, "title") else str(content)
                    source = "Yahoo Finance"
                    url = ""
                    date_str = ""
                if not title:
                    continue
                results.append(CompanyNews(
                    ticker=ticker,
                    title=title,
                    source=source,
                    date=date_str,
                    url=url,
                ))
            _log(ticker, "yahoo", "success", f"news={len(results)}")
            return results
        except Exception as e:
            _log(ticker, "yahoo", "error", f"news: {str(e)[:120]}")
            return []

    @staticmethod
    def get_market_cap(ticker: str) -> Optional[float]:
        try:
            yft = yf.Ticker(ticker)
            info = yft.info
            mc = info.get("marketCap") if info else None
            _log(ticker, "yahoo", "success" if mc else "empty", f"market_cap={mc}")
            return float(mc) if mc else None
        except Exception as e:
            _log(ticker, "yahoo", "error", f"market_cap: {str(e)[:120]}")
            return None


# ──────────────────────────────────────────────
#  Provider: FinancialDatasets.ai (fallback)
# ──────────────────────────────────────────────

class FinancialDatasetsProvider:

    @staticmethod
    def get_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        prices = fd_api.get_prices(ticker, start_date, end_date, api_key=api_key)
        _log(ticker, "financialdatasets", "success" if prices else "empty", f"prices={len(prices) if prices else 0}")
        return prices or []

    @staticmethod
    def get_financial_metrics(ticker: str, end_date: str, period: str = "ttm", limit: int = 5) -> list[FinancialMetrics]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        metrics = fd_api.get_financial_metrics(ticker, end_date, period=period, limit=limit, api_key=api_key)
        _log(ticker, "financialdatasets", "success" if metrics else "empty", f"metrics={len(metrics) if metrics else 0}")
        return metrics or []

    @staticmethod
    def get_company_news(ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 100) -> list[CompanyNews]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        news = fd_api.get_company_news(ticker, end_date, start_date=start_date, limit=limit, api_key=api_key)
        _log(ticker, "financialdatasets", "success" if news else "empty", f"news={len(news) if news else 0}")
        return news or []

    @staticmethod
    def get_market_cap(ticker: str, end_date: str) -> Optional[float]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        mc = fd_api.get_market_cap(ticker, end_date, api_key=api_key)
        _log(ticker, "financialdatasets", "success" if mc else "empty", f"market_cap={mc}")
        return mc

    @staticmethod
    def search_line_items(ticker: str, line_items: list[str], end_date: str, period: str = "ttm", limit: int = 5) -> list[LineItem]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        results = fd_api.search_line_items(ticker, line_items, end_date, period=period, limit=limit, api_key=api_key)
        return results or []

    @staticmethod
    def get_insider_trades(ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000) -> list[InsiderTrade]:
        api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        trades = fd_api.get_insider_trades(ticker, end_date, start_date=start_date, limit=limit, api_key=api_key)
        _log(ticker, "financialdatasets", "success" if trades else "empty", f"insider_trades={len(trades) if trades else 0}")
        return trades or []


# ──────────────────────────────────────────────
#  Orchestrator
# ──────────────────────────────────────────────

class MarketDataProvider:

    def __init__(self):
        self.yahoo = YahooFinanceProvider()
        self.financial_datasets = FinancialDatasetsProvider()

    # ── Prices ────────────────────────────────────────

    def get_prices(self, ticker: str, start_date: str, end_date: str) -> list[Price]:
        cache_key = f"prices_{ticker}_{start_date}_{end_date}"
        if cache_key in _PRICE_CACHE:
            return _PRICE_CACHE[cache_key]

        prices = self.yahoo.get_prices(ticker, start_date, end_date)
        if prices:
            _PRICE_CACHE[cache_key] = prices
            return prices

        _log(ticker, "orchestrator", "fallback", "Yahoo empty → trying FinancialDatasets")
        prices = self.financial_datasets.get_prices(ticker, start_date, end_date)
        if prices:
            _PRICE_CACHE[cache_key] = prices
        return prices

    # ── Financial Metrics ─────────────────────────────

    def get_financial_metrics(
        self, ticker: str, end_date: str, period: str = "ttm", limit: int = 5
    ) -> list[FinancialMetrics]:
        cache_key = f"metrics_{ticker}_{end_date}"
        if cache_key in _METRICS_CACHE:
            return _METRICS_CACHE[cache_key]

        metrics = self.yahoo.get_financial_metrics(ticker)
        if metrics:
            _METRICS_CACHE[cache_key] = metrics
            return metrics

        _log(ticker, "orchestrator", "fallback", "Yahoo empty → trying FinancialDatasets")
        metrics = self.financial_datasets.get_financial_metrics(ticker, end_date, period=period, limit=limit)
        if metrics:
            _METRICS_CACHE[cache_key] = metrics
        return metrics

    # ── Company News ──────────────────────────────────

    def get_company_news(
        self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 100
    ) -> list[CompanyNews]:
        cache_key = f"news_{ticker}_{end_date}_{limit}"
        if cache_key in _NEWS_CACHE:
            return _NEWS_CACHE[cache_key]

        news = self.yahoo.get_company_news(ticker, limit=limit)
        if news:
            _NEWS_CACHE[cache_key] = news
            return news

        _log(ticker, "orchestrator", "fallback", "Yahoo empty → trying FinancialDatasets")
        news = self.financial_datasets.get_company_news(ticker, end_date, start_date=start_date, limit=limit)
        if news:
            _NEWS_CACHE[cache_key] = news
        return news

    # ── Market Cap ────────────────────────────────────

    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        mc = self.yahoo.get_market_cap(ticker)
        if mc is not None:
            return mc
        _log(ticker, "orchestrator", "fallback", "Yahoo empty → trying FinancialDatasets")
        return self.financial_datasets.get_market_cap(ticker, end_date)

    # ── Line Items (FinancialDatasets only) ───────────

    def search_line_items(
        self, ticker: str, line_items: list[str], end_date: str, period: str = "ttm", limit: int = 5
    ) -> list[LineItem]:
        return self.financial_datasets.search_line_items(ticker, line_items, end_date, period=period, limit=limit)

    # ── Insider Trades (FinancialDatasets only) ───────

    def get_insider_trades(
        self, ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000
    ) -> list[InsiderTrade]:
        return self.financial_datasets.get_insider_trades(ticker, end_date, start_date=start_date, limit=limit)


# ── Singleton instance ───────────────────────────────────
_provider: Optional[MarketDataProvider] = None


def get_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        _provider = MarketDataProvider()
    return _provider


# ── Module-level convenience functions ───────────────────
# These match the existing signatures in src.tools.api
# so agents can import them with minimal changes.

def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]:
    return get_provider().get_prices(ticker, start_date, end_date)


def get_financial_metrics(
    ticker: str, end_date: str, period: str = "ttm", limit: int = 5, api_key: str = None
) -> list[FinancialMetrics]:
    return get_provider().get_financial_metrics(ticker, end_date, period=period, limit=limit)


def get_company_news(
    ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 100, api_key: str = None
) -> list[CompanyNews]:
    return get_provider().get_company_news(ticker, end_date, start_date=start_date, limit=limit)


def get_market_cap(ticker: str, end_date: str, api_key: str = None) -> Optional[float]:
    return get_provider().get_market_cap(ticker, end_date)


def search_line_items(
    ticker: str, line_items: list[str], end_date: str, period: str = "ttm", limit: int = 5, api_key: str = None
) -> list[LineItem]:
    return get_provider().search_line_items(ticker, line_items, end_date, period=period, limit=limit)


def get_insider_trades(
    ticker: str, end_date: str, start_date: Optional[str] = None, limit: int = 1000, api_key: str = None
) -> list[InsiderTrade]:
    return get_provider().get_insider_trades(ticker, end_date, start_date=start_date, limit=limit)
