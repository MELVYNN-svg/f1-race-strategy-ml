
from kedro.pipeline import Pipeline, node

from .nodes import get_schedule, download_all


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        node(
            func=get_schedule,
            inputs="params:year",
            outputs="fastf1_schedule",
            name="get_schedule",
        ),
        node(
            func=download_all,
            inputs=["fastf1_schedule", "params:year"],
            outputs="fastf1_ingestion_report",
            name="download_all",
        ),
    ])
