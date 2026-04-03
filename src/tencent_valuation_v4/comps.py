from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import ProjectPaths


class CompsError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompsArtifacts:
    peer_multiples: Path
    relative_valuation_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> CompsArtifacts:
    return CompsArtifacts(
        peer_multiples=paths.data_model / "peer_multiples.csv",
        relative_valuation_outputs=paths.data_model / "relative_valuation_outputs.csv",
    )


# Scenario stress haircuts applied to the base relative valuation
_SCENARIO_EQUITY_HAIRCUT = {
    "base": 1.00,
    "bad": 0.85,
    "extreme": 0.70,
}


def _load_peer_fundamentals(paths: ProjectPaths, asof: str, peers: list[str]) -> pd.DataFrame | None:
    """
    Load actual peer fundamentals from override file if available.
    Returns DataFrame with columns: ticker, net_income_hkd_bn, book_value_hkd_bn,
    ebit_hkd_bn, fcf_hkd_bn — or None if not present.
    """
    override_path = paths.data_raw / asof / "peer_fundamentals.csv"
    if not override_path.exists():
        return None

    df = pd.read_csv(override_path)
    required = {"ticker", "net_income_hkd_bn", "book_value_hkd_bn", "ebit_hkd_bn", "fcf_hkd_bn"}
    if not required.issubset(set(df.columns)):
        warnings.warn(
            f"peer_fundamentals.csv at {override_path} missing columns for comps: "
            f"{required - set(df.columns)}. Falling back to proxy.",
            stacklevel=2,
        )
        return None

    df = df[df["ticker"].isin(peers)].copy()
    if df.empty:
        return None
    return df


def run_comps(
    asof: str,
    paths: ProjectPaths,
    peers: list[str],
    wacc_components_path: Path,
    scenarios_config: dict | None = None,
) -> CompsArtifacts:
    """
    Relative valuation via peer multiples.

    Computes real P/E, P/B, EV/EBIT, EV/FCF from actual peer financial data when
    available in peer_fundamentals.csv (columns: net_income_hkd_bn, book_value_hkd_bn,
    ebit_hkd_bn, fcf_hkd_bn). Falls back to a proxy using market-implied anchors with
    a logged warning when the override file is absent or incomplete.

    Produces one row per scenario (base/bad/extreme). Bad and extreme scenarios apply
    haircuts to the base relative valuation to reflect peer re-rating in downturns.
    """
    paths.ensure()
    artifacts = _default_artifacts(paths)

    market = pd.read_csv(paths.data_processed / "market_inputs.csv")
    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    wacc = pd.read_csv(wacc_components_path)

    if fin.empty or wacc.empty:
        raise CompsError("Missing required inputs for comps")

    tax = float(wacc.iloc[0]["tax_rate_tencent"])

    target_fin = fin.iloc[0]
    target_price = float(target_fin["current_price_hkd"])
    target_shares = float(target_fin["shares_out_bn"])
    target_equity = target_price * target_shares

    target_ticker_row = market.loc[market["ticker"] == "0700.HK"]
    if target_ticker_row.empty:
        raise CompsError("0700.HK not found in market_inputs.csv")
    target_debt = float(target_ticker_row.iloc[0]["gross_debt_hkd_bn"])
    target_net_cash = float(target_fin["net_cash_hkd_bn"])
    target_enterprise = target_equity + target_debt - target_net_cash

    target_revenue = float(target_fin["revenue_hkd_bn"])
    target_ebit = target_revenue * float(target_fin["ebit_margin"])
    target_fcf = target_revenue * (
        float(target_fin["ebit_margin"]) * (1.0 - tax)
        + float(target_fin["dep_pct_revenue"])
        - float(target_fin["capex_pct_revenue"])
    )
    target_net_income = target_ebit * (1.0 - tax)
    # Use actual book value if available, otherwise proxy
    if "book_value_hkd_bn" in target_fin.index and not pd.isna(target_fin["book_value_hkd_bn"]):
        target_book = float(target_fin["book_value_hkd_bn"])
    else:
        target_book = max(1e-6, 0.42 * target_revenue + max(target_net_cash, 0.0))

    # Load peer fundamentals: real data preferred, proxy as fallback
    peer_fundamentals = _load_peer_fundamentals(paths, asof, peers)
    using_real_data = peer_fundamentals is not None
    if not using_real_data:
        warnings.warn(
            f"No peer_fundamentals.csv found at data/raw/{asof}/ with required columns "
            "(net_income_hkd_bn, book_value_hkd_bn, ebit_hkd_bn, fcf_hkd_bn). "
            "Using proxy multiples — comps results will be approximate.",
            stacklevel=2,
        )

    peer_rows: list[dict[str, float | str]] = []
    for ticker in peers:
        prow = market.loc[market["ticker"] == ticker]
        if prow.empty:
            continue
        equity = float(prow.iloc[0]["market_equity_hkd_bn"])
        debt = float(prow.iloc[0]["gross_debt_hkd_bn"])
        # Correct EV = equity + debt - cash; use gross_debt as proxy for net debt when cash unavailable
        # market_inputs may have net_cash_hkd_bn for peers; fall back to debt-only if absent
        if "net_cash_hkd_bn" in prow.columns:
            peer_cash = float(prow.iloc[0]["net_cash_hkd_bn"])
            ev = equity + debt - peer_cash
        else:
            ev = equity + debt  # conservative (slightly overstates EV)

        if using_real_data:
            frow = peer_fundamentals.loc[peer_fundamentals["ticker"] == ticker]
            if frow.empty:
                continue
            net_income = float(frow.iloc[0]["net_income_hkd_bn"])
            book = float(frow.iloc[0]["book_value_hkd_bn"])
            ebit = float(frow.iloc[0]["ebit_hkd_bn"])
            fcf = float(frow.iloc[0]["fcf_hkd_bn"])
        else:
            # Proxy: derive from market-implied anchors (static, approximate)
            # These are conservative estimates used only when real data unavailable
            _pe_proxy = {"9988.HK": 12.0, "3690.HK": 22.0, "9999.HK": 18.0, "9618.HK": 14.0, "9888.HK": 16.0}
            _pb_proxy = {"9988.HK": 1.8, "3690.HK": 5.2, "9999.HK": 2.1, "9618.HK": 1.7, "9888.HK": 2.4}
            _ev_ebit_proxy = {"9988.HK": 12.5, "3690.HK": 28.0, "9999.HK": 18.5, "9618.HK": 11.5, "9888.HK": 15.5}
            _ev_fcf_proxy = {"9988.HK": 17.0, "3690.HK": 31.0, "9999.HK": 22.0, "9618.HK": 15.0, "9888.HK": 20.0}
            net_income = equity / _pe_proxy.get(ticker, 15.0)
            book = equity / _pb_proxy.get(ticker, 2.0)
            ebit = ev / _ev_ebit_proxy.get(ticker, 15.0)
            fcf = ev / _ev_fcf_proxy.get(ticker, 20.0)

        pe = equity / max(1e-6, net_income)
        pb = equity / max(1e-6, book)
        ev_ebit = ev / max(1e-6, ebit)
        ev_fcf = ev / max(1e-6, fcf)

        peer_rows.append(
            {
                "asof": asof,
                "ticker": ticker,
                "equity_value_hkd_bn": equity,
                "enterprise_value_hkd_bn": ev,
                "net_income_hkd_bn": net_income,
                "book_value_hkd_bn": book,
                "ebit_hkd_bn": ebit,
                "fcf_hkd_bn": fcf,
                "pe": pe,
                "pb": pb,
                "ev_ebit": ev_ebit,
                "ev_fcf": ev_fcf,
                "data_source": "real" if using_real_data else "proxy",
            }
        )

    peer_table = pd.DataFrame(peer_rows)
    if peer_table.empty:
        raise CompsError("No peer rows for comps")

    peer_table.to_csv(artifacts.peer_multiples, index=False)

    med_pe = float(peer_table["pe"].median())
    med_pb = float(peer_table["pb"].median())
    med_ev_ebit = float(peer_table["ev_ebit"].median())
    med_ev_fcf = float(peer_table["ev_fcf"].median())

    # Base implied equity from each multiple method
    implied_equity_pe = med_pe * target_net_income
    implied_equity_pb = med_pb * target_book
    implied_equity_ev_ebit = med_ev_ebit * target_ebit - target_debt + target_net_cash
    implied_equity_ev_fcf = med_ev_fcf * target_fcf - target_debt + target_net_cash

    implied_equity_base = float(np.nanmean([
        implied_equity_pe,
        implied_equity_pb,
        implied_equity_ev_ebit,
        implied_equity_ev_fcf,
    ]))
    fair_base = implied_equity_base / target_shares

    # Produce one row per scenario; bad/extreme apply haircuts to reflect peer re-rating
    out_rows: list[dict[str, float | str]] = []
    for scenario, haircut in _SCENARIO_EQUITY_HAIRCUT.items():
        implied_equity = implied_equity_base * haircut
        fair = fair_base * haircut
        out_rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "method": "relative",
                "median_pe": med_pe,
                "median_pb": med_pb,
                "median_ev_ebit": med_ev_ebit,
                "median_ev_fcf": med_ev_fcf,
                "equity_value_hkd_bn": round(implied_equity, 4),
                "fair_value_hkd_per_share": round(fair, 4),
                "current_equity_value_hkd_bn": target_equity,
                "current_enterprise_value_hkd_bn": target_enterprise,
                "scenario_haircut": haircut,
                "data_source": "real" if using_real_data else "proxy",
            }
        )

    pd.DataFrame(out_rows).to_csv(artifacts.relative_valuation_outputs, index=False)
    return artifacts
