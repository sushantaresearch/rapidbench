"""V1b: Great Expectations adapter (SCAFFOLD; not smoke-tested in this
sandbox because the GX install is heavy). The nine rules in rules.py are the
reference implementations; this adapter re-expresses them as a GX expectation
suite so the paper can report tool-native results. Run locally:
    pip install great_expectations
"""
from __future__ import annotations

import pandas as pd

EXPECTATIONS = [
    ("expect_column_values_to_match_regex", {"column": "hs6", "regex": r"^\d{6}$"}),
    ("expect_column_values_to_be_between", {"column": "cif_usd", "min_value": 1e-9}),
    ("expect_compound_columns_to_be_unique",
     {"column_list": ["importer_id", "hs6", "month", "qty", "cif_usd"]}),
]


def gx_suite_fired(reference: pd.DataFrame, current: pd.DataFrame) -> dict[str, bool]:
    import great_expectations as gx  # noqa: local heavy dependency
    ctx = gx.get_context(mode="ephemeral")
    ds = ctx.data_sources.add_pandas("rapidbench")
    asset = ds.add_dataframe_asset("current")
    batch = asset.add_batch_definition_whole_dataframe("b").get_batch(
        batch_parameters={"dataframe": current})
    fired = {}
    for name, kwargs in EXPECTATIONS:
        exp = getattr(gx.expectations, _camel(name))(**kwargs)
        fired[name] = not batch.validate(exp).success
    return fired


def _camel(snake: str) -> str:
    return "".join(w.capitalize() for w in snake.split("_"))
