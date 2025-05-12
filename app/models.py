from pydantic import BaseModel

class UserRegeristrationModel(BaseModel):
    user: str
    password: str

class FundDetailsModel(BaseModel):
    amount: float
    scheme_code: int