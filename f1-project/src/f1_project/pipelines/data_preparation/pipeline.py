"""Prepare les donnees locales, sans reseau ni nouvel import."""

from kedro.pipeline import Pipeline, node

from .nodes import TABLES, build_inventory, build_sessions, concatenate_tables


def create_pipeline(**kwargs) -> Pipeline:
    outputs = {
        f"fastf1_{'events' if table == 'event' else table}": f"fastf1_{'events' if table == 'event' else table}"
        for table in TABLES
    }
    return Pipeline(
        [
            node(
                build_inventory,
                inputs=["fastf1_raw", "params:year"],
                outputs="fastf1_inventory",
                name="inventory_local_fastf1",
            ),
            node(
                concatenate_tables,
                inputs=["fastf1_raw", "params:year"],
                outputs=outputs,
                name="prepare_fastf1_tables",
            ),
            node(
                build_sessions,
                inputs=["fastf1_inventory", "fastf1_schedule"],
                outputs="fastf1_sessions",
                name="check_available_sessions",
            ),
        ]
    )
