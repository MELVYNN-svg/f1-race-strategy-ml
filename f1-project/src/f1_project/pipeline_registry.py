"""Project pipelines."""

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline
from .pipelines.data_ingestion import create_pipeline


def register_pipelines() -> dict[str, Pipeline]:

    data_ingestion = create_pipeline()

    return{
        "__default__": data_ingestion,
        "data_ingestion": data_ingestion,
    }
