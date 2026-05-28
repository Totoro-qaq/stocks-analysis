from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SUPPORTED_ACTIONS = {"exclude", "cap", "floor", "boost", "penalize", "note"}


@dataclass(frozen=True)
class RuleSet:
    min_weights: pd.Series
    max_weights: pd.Series
    return_multipliers: pd.Series
    risk_multipliers: pd.Series
    active_rules: pd.DataFrame


def load_rules(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return empty_rules()
    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    rules = pd.read_csv(rules_path)
    required = {
        "ticker",
        "start_date",
        "end_date",
        "action",
        "min_weight",
        "max_weight",
        "return_multiplier",
        "risk_multiplier",
        "reason",
    }
    missing = required - set(rules.columns)
    if missing:
        raise ValueError(f"Rules file missing columns: {sorted(missing)}")

    rules = rules.copy()
    rules["ticker"] = rules["ticker"].astype(str).str.upper().str.strip()
    rules["action"] = rules["action"].astype(str).str.lower().str.strip()
    invalid = sorted(set(rules["action"]) - SUPPORTED_ACTIONS)
    if invalid:
        raise ValueError(f"Unsupported rule actions: {invalid}")

    rules["start_date"] = pd.to_datetime(rules["start_date"], errors="coerce")
    rules["end_date"] = pd.to_datetime(rules["end_date"], errors="coerce")
    for column in ["min_weight", "max_weight", "return_multiplier", "risk_multiplier"]:
        rules[column] = pd.to_numeric(rules[column], errors="coerce")
    rules["reason"] = rules["reason"].fillna("")
    return rules


def empty_rules() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "ticker",
            "start_date",
            "end_date",
            "action",
            "min_weight",
            "max_weight",
            "return_multiplier",
            "risk_multiplier",
            "reason",
        ]
    )


def active_rules_for_date(rules: pd.DataFrame, as_of_date: pd.Timestamp | str) -> pd.DataFrame:
    if rules.empty:
        return rules.copy()
    as_of = pd.Timestamp(as_of_date)
    start_ok = rules["start_date"].isna() | (rules["start_date"] <= as_of)
    end_ok = rules["end_date"].isna() | (rules["end_date"] >= as_of)
    return rules[start_ok & end_ok].copy()


def build_rule_set(
    tickers: list[str],
    rules: pd.DataFrame,
    as_of_date: pd.Timestamp | str,
    default_max_weight: float,
) -> RuleSet:
    index = pd.Index(tickers, name="ticker")
    min_weights = pd.Series(0.0, index=index)
    max_weights = pd.Series(default_max_weight, index=index)
    return_multipliers = pd.Series(1.0, index=index)
    risk_multipliers = pd.Series(1.0, index=index)

    active = active_rules_for_date(rules, as_of_date)
    active = active[active["ticker"].isin(index)].copy()

    for rule in active.itertuples(index=False):
        ticker = rule.ticker
        action = rule.action
        min_weight = none_if_nan(rule.min_weight)
        max_weight = none_if_nan(rule.max_weight)
        return_multiplier = none_if_nan(rule.return_multiplier)
        risk_multiplier = none_if_nan(rule.risk_multiplier)

        if action == "exclude":
            min_weights.loc[ticker] = 0.0
            max_weights.loc[ticker] = 0.0
        elif action == "cap":
            if max_weight is not None:
                max_weights.loc[ticker] = min(max_weights.loc[ticker], max_weight)
            if min_weight is not None:
                min_weights.loc[ticker] = max(min_weights.loc[ticker], min_weight)
        elif action == "floor":
            if min_weight is not None:
                min_weights.loc[ticker] = max(min_weights.loc[ticker], min_weight)
            if max_weight is not None:
                max_weights.loc[ticker] = min(max_weights.loc[ticker], max_weight)
        elif action == "boost":
            if return_multiplier is not None:
                return_multipliers.loc[ticker] *= return_multiplier
            if max_weight is not None:
                max_weights.loc[ticker] = min(max_weights.loc[ticker], max_weight)
            if min_weight is not None:
                min_weights.loc[ticker] = max(min_weights.loc[ticker], min_weight)
        elif action == "penalize":
            if return_multiplier is not None:
                return_multipliers.loc[ticker] *= return_multiplier
            if risk_multiplier is not None:
                risk_multipliers.loc[ticker] *= risk_multiplier
            if max_weight is not None:
                max_weights.loc[ticker] = min(max_weights.loc[ticker], max_weight)
            if min_weight is not None:
                min_weights.loc[ticker] = max(min_weights.loc[ticker], min_weight)
        elif action == "note":
            continue

    impossible = min_weights > max_weights
    if impossible.any():
        bad = ", ".join(impossible[impossible].index.tolist())
        raise ValueError(f"Rules create min_weight > max_weight for: {bad}")

    if max_weights.sum() < 1 - 1e-9:
        raise ValueError(
            f"Rules are infeasible: max weight capacity is {max_weights.sum():.4f}, below required total weight 1.0"
        )
    if min_weights.sum() > 1 + 1e-9:
        raise ValueError(
            f"Rules are infeasible: min weight requirement is {min_weights.sum():.4f}, above required total weight 1.0"
        )

    return RuleSet(
        min_weights=min_weights,
        max_weights=max_weights,
        return_multipliers=return_multipliers,
        risk_multipliers=risk_multipliers,
        active_rules=active,
    )


def none_if_nan(value):
    if value is None:
        return None
    try:
        if np.isnan(value):
            return None
    except TypeError:
        return value
    return value


def adjusted_mean_returns(mean_returns: pd.Series, rule_set: RuleSet) -> pd.Series:
    return mean_returns * rule_set.return_multipliers.reindex(mean_returns.index).fillna(1.0)


def adjusted_covariance(covariance: pd.DataFrame, rule_set: RuleSet) -> pd.DataFrame:
    multipliers = rule_set.risk_multipliers.reindex(covariance.index).fillna(1.0)
    scale = np.outer(multipliers.values, multipliers.values)
    adjusted = covariance.values * scale
    return pd.DataFrame(adjusted, index=covariance.index, columns=covariance.columns)


def bounds_from_rules(tickers: list[str], rule_set: RuleSet) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(rule_set.min_weights.loc[ticker]), float(rule_set.max_weights.loc[ticker]))
        for ticker in tickers
    )


def export_active_rules(rule_set: RuleSet, output_path: Path) -> None:
    active = rule_set.active_rules.copy()
    if active.empty:
        active = empty_rules()
    active.to_csv(output_path, index=False)
