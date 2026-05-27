from ..albums import CardResponse
from ..base import BaseSchema


class TradeOptionsResponse(BaseSchema):
    current_user_needs: list[CardResponse]
    other_user_needs: list[CardResponse]
