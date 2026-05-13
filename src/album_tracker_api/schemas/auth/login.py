from pydantic import BaseModel

from ..users import MeResponse


# Use BaseModel and not BaseSchema since OAuth standard requires
# snake_case fields
class LoginResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    user: MeResponse
