from ..base import BaseSchema


class HealthCheckResponse(BaseSchema):
    status: str
