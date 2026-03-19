from __future__ import annotations

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


def run_comps(asof: str, paths: ProjectPaths, peers: list[str], wacc_components_path: Path) -> CompsArtifacts:
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
    target_debt = float(market.loc[market["ticker"] == "0700.HK", "gross_debt_hkd_bn"].iloc[0])
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
    target_book = max(1e-6, 0.42 * target_revenue + max(target_net_cash, 0.0))

    # Proxy peer fundamentals via conservative market-implied anchors.
    pe_anchor = {
        "9988.HK": 12.0,
        "3690.HK": 22.0,
        "9999.HK": 18.0,
        "9618.HK": 14.0,
        "9888.HK": 16.0,
    }
    pb_anchor = {
        "9988.HK": 1.8,
        "3690.HK": 5.2,
        "9999.HK": 2.1,
        "9618.HK": 1.7,
        "9888.HK": 2.4,
    }
    ev_ebit_anchor = {
        "9988.HK": 12.5,
        "3690.HK": 28.0,
        "9999.HK": 18.5,
        "9618.HK": 11.5,
        "9888.HK": 15.5,
    }
    ev_fcf_anchor = {
        "9988.HK": 17.0,
        "3690.HK": 31.0,
        "9999.HK": 22.0,
        "9618.HK": 15.0,
        "9888.HK": 20.0,
    }

    peer_rows: list[dict[str, float | str]] = []
    for ticker in peers:
        prow = market.loc[market["ticker"] == ticker]
        if prow.empty:
            continue
        equity = float(prow.iloc[0]["market_equity_hkd_bn"])
        debt = float(prow.iloc[0]["gross_debt_hkd_bn"])
        ev = equity + debt

        pe = float(pe_anchor.get(ticker, 15.0))
        pb = float(pb_anchor.get(ticker, 2.0))
        ev_ebit = float(ev_ebit_anchor.get(ticker, 15.0))
        ev_fcf = float(ev_fcf_anchor.get(ticker, 20.0))

        net_income = equity / pe
        book = equity / pb
        ebit = ev / ev_ebit
        fcf = ev / ev_fcf

        peer_rows.append(
            {
                "asof": asof,
                "ticker": ticker,
                "equity_value_hkd_bn": equity,
                "enterprise_value_hkd_bn": ev,
                "net_income_hkd_bn_proxy": net_income,
                "book_value_hkd_bn_proxy": book,
                "ebit_hkd_bn_proxy": ebit,
                "fcf_hkd_bn_proxy": fcf,
                "pe": equity / max(1e-6, net_income),
                "pb": equity / max(1e-6, book),
                "ev_ebit": ev / max(1e-6, ebit),
                "ev_fcf": ev / max(1e-6, fcf),
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

    implied_equity_pe = med_pe * target_net_income
    implied_equity_pb = med_pb * target_book
    implied_equity_ev_ebit = med_ev_ebit * target_ebit - target_debt + target_net_cash
    implied_equity_ev_fcf = med_ev_fcf * target_fcf - target_debt + target_net_cash

    implied_equity = np.nanmean([implied_equity_pe, implied_equity_pb, implied_equity_ev_ebit, implied_equity_ev_fcf])
    fair = implied_equity / target_shares

    pd.DataFrame(
        [
            {
                "asof": asof,
                "scenario": "base",
                "method": "relative",
                "median_pe": med_pe,
                "median_pb": med_pb,
                "median_ev_ebit": med_ev_ebit,
                "median_ev_fcf": med_ev_fcf,
                "equity_value_hkd_bn": implied_equity,
                "fair_value_hkd_per_share": fair,
                "current_equity_value_hkd_bn": target_equity,
                "current_enterprise_value_hkd_bn": target_enterprise,
            }
        ]
    ).to_csv(artifacts.relative_valuation_outputs, index=False)

    return artifacts
