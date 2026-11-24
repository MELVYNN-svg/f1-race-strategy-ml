"""Project pipelines."""

from kedro.pipeline import Pipeline, node

from .fastf1_archive import write_audit
from .pipelines.data_ingestion import create_pipeline as ingestion_pipeline
from .pipelines.data_preparation import create_pipeline as preparation_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    data_ingestion = ingestion_pipeline()
    data_preparation = preparation_pipeline()

    return {
        "__default__": data_preparation,
        "data_ingestion": data_ingestion,
        "data_preparation": data_preparation,
        "data_quality": Pipeline(
            [
                node(
                    write_audit,
                    inputs=["fastf1_schedule", "params:year"],
                    outputs=["fastf1_coverage", "fastf1_quality"],
                    name="audit_fastf1_content",
                )
            ]
        ),
    }
