from album_tracker_api.schemas.base import BaseSchema


class HealthCheckResponse(BaseSchema):
    status: str
