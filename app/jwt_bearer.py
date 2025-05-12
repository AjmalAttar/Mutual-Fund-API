from fastapi import Request, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
# from jwt_handler import decode_jwt
from database import Database, config
from datetime import datetime, timedelta
from loguru import logger

apikey_header = APIKeyHeader(name="mutual_fund", auto_error=False)

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        try:
            logger.info("__call__ method in JWTBearer class")
            credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
            token = credentials.credentials
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                if not await self.verify_session_token(token):
                    raise HTTPException(status_code=403, detail="Invalid token or expired token.")
                else:
                    return credentials.credentials
            else:
                raise HTTPException(status_code=403, detail="Invalid authorization code.")
        except Exception as e:
            logger.exception("JWTBearer __call__ exception",e)
        
    async def verify_session_token(self, token):
        """Func helps to verify the JWT session
        """        

        apiKey = await self.get_session_apikey(token)
        return apiKey

    async def get_session_apikey(self, token: str = Security(apikey_header)):
        """Func helps to validate the JWT token
        """
        try:
            session_exp_result_ = await Database.get_collection("user_profile").find_one({"token": token})
            if session_exp_result_:
                session_exp_result = str(session_exp_result_['session_exp'])
                current_time = str(datetime.now())
                if session_exp_result <= current_time:
                    logger.info("session has expired")
                    await Database.get_collection("user_profile").update_one({"token": token},{'$unset': {'session_exp': 1, 'token': 1}})
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session Expired, Please create new session token")
                    return False
                else:
                    logger.info("session NOT expired")
                    await Database.get_collection("user_profile").update_one({"token": token},{'$set': {'session_exp': datetime.now() + timedelta(minutes= int(config["token_expire"]) )}})
                    return True               
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Session Key")

        except Exception as er:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Session Key")