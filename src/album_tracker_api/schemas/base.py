from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


# https://stackoverflow.com/questions/67995510/how-to-inflect-from-snake-case-to-camel-case-post-the-pydantic-schema-validation
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
        json_schema_serialization_defaults_required=True,
    )


class IdTextPair(BaseSchema):
    id: UUID
    text: str


class BaseResponse[T](BaseSchema):
    data: T
    message: str = ""
