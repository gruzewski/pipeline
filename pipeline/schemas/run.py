from enum import Enum
import datetime
from typing import List, Optional, Union

from pydantic import validator, root_validator

from .base import BaseModel
from .data import DataGet
from .runnable import (
    FunctionGet,
    FunctionGetDetailed,
    RunnableIOGet,
    PipelineGet,
    PipelineGetDetailed,
)
from .tag import TagGet
from .token import TokenGet


class RunState(Enum):
    RECEIVED = "received"
    ALLOCATING_CLUSTER = "allocating_cluster"
    ALLOCATING_RESOURCE = "allocating_resource"
    LOADING_DATA = "loading_data"
    LOADING_FUNCTION = "loading_function"
    LOADING_PIPELINE = "loading_pipeline"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class RunCreate(BaseModel):
    pipeline_id: Optional[str]
    function_id: Optional[str]
    data: Optional[str]
    data_id: Optional[str]

    @root_validator
    def pipeline_or_function(cls, values):
        pipeline_id, function_id = values.get("pipeline_id"), values.get("function_id")

        pipeline_defined = pipeline_id != None
        function_defined = function_id != None

        if pipeline_defined == function_defined:
            raise ValueError("You must define either a pipeline_id OR function_id.")

        return values

    @validator("data_id")
    def validate_data_id(cls, value, **kwargs):
        if kwargs.get("values", {}).get("data") is not None:
            raise ValueError("Can only pass in data or data_id, not both.")
        elif value is None:
            raise ValueError("Must pass in data or data_id")
        return value


class RunIOGet(RunnableIOGet):
    """Realised/given input/output data to a Runnable used in a Run."""

    value: str
    data_url: str


class RunGet(BaseModel):
    id: str
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]
    run_state: RunState
    compute_time_ms: Optional[int]
    runnable: Union[FunctionGet, PipelineGet]
    data: DataGet
    blocking: Optional[bool] = False

    class Config:
        allow_population_by_field_name = True


class RunGetDetailed(RunGet):
    runnable: Union[FunctionGetDetailed, PipelineGetDetailed]
    n_resources: int
    resource_type: str
    region: str
    tags: List[TagGet] = []
    inputs: List[RunIOGet] = []
    outputs: List[RunIOGet] = []
    token: TokenGet
