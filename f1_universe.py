"""Utility functions for selecting a trading universe."""
from typing import List, Dict


def get_top_volume_tickers() -> List[str]:
    """Return a list of tickers with the highest trading volume.

    This placeholder implementation simply returns static sample data.
    """
    return ["BTC", "ETH", "XRP", "ADA", "SOL"]


def apply_filters(tickers: List[str], config: Dict) -> List[str]:
    """Apply filter conditions to the given tickers.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols.
    config : dict
        Dictionary with filter values such as price, volatility, tick
        and spread.

    Returns
    -------
    list[str]
        Filtered list of ticker symbols.
    """
    # Placeholder: filtering logic to be implemented later
    return tickers


def select_universe(config: Dict | None = None) -> List[str]:
    """Select the final universe of tradable tickers.

    Parameters
    ----------
    config : dict, optional
        Filter configuration that will be passed to :func:`apply_filters`.

    Returns
    -------
    list[str]
        Final list of ticker symbols.
    """
    tickers = get_top_volume_tickers()
    return apply_filters(tickers, config or {})
