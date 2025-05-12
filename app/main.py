from fastapi import FastAPI, HTTPException, Depends, status
from models import UserRegeristrationModel,FundDetailsModel
from loguru import logger
from database import Database,config
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi.responses import JSONResponse
import httpx
import asyncio
from jwt_bearer import JWTBearer
from fastapi.security import HTTPBearer
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import time
# app instance for all APIs
app = FastAPI()

RAPIDAPI_KEY = config["RAPIDAPI_KEY"]
security_scheme = HTTPBearer()

# welcome message API
@app.get("/")
async def welcome():
    return "Welcome to Mutual Fund Application"

# Register user
@app.post("/register")
async def register(userdetails: UserRegeristrationModel):
    try:
        logger.info("Enter in register in Main")
        if userdetails.user == "string" or userdetails.password == "string":
            return "Please provide valid user and password"
        user_exists = await Database.get_collection("user_profile").find_one({"user": userdetails.user},{"_id":0})
        if user_exists:
            return "Username already Exists"
        Database.get_collection("user_profile").insert_one({"user": userdetails.user, "password": userdetails.password})        
        return "User Registered Successfully"
    except Exception as err:
        logger.exception("Exception in register method in main - %s"%err)
        raise HTTPException(status_code=400, detail="Failed to register User")

@app.post("/login")
async def login(userdetails: UserRegeristrationModel):
    try:
        logger.info("Enter in Login in Main")
        user_exists = await Database.get_collection("user_profile").find_one({"user": userdetails.user, "password": userdetails.password},{"_id":0})
        if user_exists:
            exp_time = datetime.now() + timedelta(minutes=int(config["token_expire"]))
            payload = {"user": userdetails.user, "exp": exp_time}
            token = jwt.encode(payload, config["secret_key"], algorithm=config["algorithm"])
            await Database.get_collection("user_profile").update_one({"user": userdetails.user},{"$set": {"session_exp": exp_time,"token":token}})
            data = {"token": token}
            return JSONResponse(status_code=200, content=data)
        else:
            return "User Credentials are wrong"
    except Exception as er:
        logger.exception("Exception in login : %s"%er)

# api with Host "latest-mutual-fund-nav.p.rapidapi.com"
@app.get("/fund-families", dependencies=[Depends(JWTBearer())])
async def get_fund_families():
    """
        API to get all Mutual funds
    """
    try:
        logger.info("Enter in get_fund_families in Main")
        url="https://latest-mutual-fund-nav.p.rapidapi.com/latest?Scheme_Type=Open"
        #url = "https://latest-mutual-fund-nav.p.rapidapi.com/fund_family_list"
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "latest-mutual-fund-nav.p.rapidapi.com"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
        return r.json()
    except Exception as err:
        logger.exception("Exception in get_fund_families in Main : %s"%err)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config["secret_key"], algorithms=[config["algorithm"]])
        return payload.get("user")        
    except Exception as er:
        logger.exception("Exception in get_fund_details in Main : %s"%er)
        
@app.get("/get-fund-details", dependencies=[Depends(JWTBearer())])
async def get_fund_details(scheme_code:int):
    """
        API to get details of particular mutual fund
        params: scheme_code
        return: mutual fund details
    """
    try:
        logger.info("Enter in get_fund_details in Main")
        url="https://nav-indian-mutual-fund.p.rapidapi.com/nav?scheme_code=%s"%scheme_code
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "nav-indian-mutual-fund.p.rapidapi.com"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
        return r.json()
    except Exception as err:
        logger.exception("Exception in get_fund_details in Main : %s"%err)

@app.post("/invest", dependencies=[Depends(JWTBearer())])
async def invest(fund_details: FundDetailsModel, user=Depends(get_current_user)):
    try:
        logger.info("Enter in invest in Main")
        print(">> invest user >>>>",type(user),user)
        existing_portfolio = await Database.get_collection("user_profile").find_one({"user": user},{"_id":0,"portfolio":1})
        print(">> existing_portfolio >>>>",type(existing_portfolio),existing_portfolio)
        print(">>> one >>>>",existing_portfolio.get("portfolio",{}).get(str(fund_details.scheme_code),{}).get("invested_amount",0))
        print(">>> two >>>>",fund_details.amount)
        new_investment = existing_portfolio.get("portfolio",{}).get(str(fund_details.scheme_code),{}).get("invested_amount",0) + fund_details.amount
        await Database.get_collection("user_profile").update_one({"user": user},
            {"$set":{"portfolio.%s"%(fund_details.scheme_code): {"invested_amount": new_investment}}})
        return "Investment added"
    except Exception as err:
        logger.exception("Exception in invest in Main : %s"%err)

@app.get("/portfolio", dependencies=[Depends(JWTBearer())])
async def get_portfolio(user=Depends(get_current_user)):
    try:
        logger.info("Enter in get_portfolio in Main")
        print(">>> portfolio user >>>>",user)
        portfolio_details = await Database.get_collection("user_profile").find_one({"user":user},{"_id":0,"portfolio":1})
        portfolio = portfolio_details.get("portfolio",{})
        updated = []
        async with httpx.AsyncClient() as client:
            for fund_scheme_code, fund in portfolio.items():
                url="https://nav-indian-mutual-fund.p.rapidapi.com/nav?scheme_code=%s"%fund_scheme_code
                headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "nav-indian-mutual-fund.p.rapidapi.com"}
                r = await client.get(url, headers=headers)
                nav_data = r.json()
                current_nav = float(nav_data.get("data",{}).get("NAV", 0))
                current_value = round(current_nav * fund.get("invested_amount",1), 2)
                updated.append({"scheme_code": fund_scheme_code, "Amount Invested": fund.get("invested_amount",1), "Total Value": current_value})
        return updated
    except Exception as err:
        logger.exception("Exception in get_portfolio in Main : %s"%err)

async def update_portfolio_values():
    try:
        logger.info("Enter in update_portfolio_values in Main")
        # portfolio_details = await Database.get_collection("user_profile").find({},{"_id":0,"portfolio":1})
        portfolio_details = []
        async for document in Database.get_collection("user_profile").find({},{"_id":0,"user":1,"portfolio":1}):
            portfolio_details.append(document)
        updated = []
        async with httpx.AsyncClient() as client:
            for portfolio in portfolio_details:
                for fund_scheme_code, fund in portfolio.get("portfolio",{}).items():
                    url="https://nav-indian-mutual-fund.p.rapidapi.com/nav?scheme_code=%s"%fund_scheme_code
                    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "nav-indian-mutual-fund.p.rapidapi.com"}
                    r = await client.get(url, headers=headers)
                    nav_data = r.json()
                    current_nav = float(nav_data.get("data",{}).get("NAV", 0))
                    current_value = round(current_nav * fund.get("invested_amount",1), 2)
                    await Database.get_collection("user_profile").update_one({"user": portfolio.get("user","")},
                        {"$set":{"portfolio.%s"%fund_scheme_code: {"invested_amount":fund.get("invested_amount",1),"total_value":current_value}}})
    except Exception as err:
        logger.exception("Exception in update_portfolio_values in Main : %s"%err)

async def scheduler():
    try:
        logger.info("Enter in scheduler in Main")
        while True:
            await update_portfolio_values()
            await asyncio.sleep(3600)  # Every hour
    except Exception as err:
        logger.exception("Exception in scheduler in Main : %s"%err)

# @app.on_event("startup")
# async def start_scheduler():
#     try:
#         logger.info("Enter in start_scheduler in Main")
#         asyncio.create_task(scheduler())
#     except Exception as err:
#         logger.exception("Exception in start_scheduler in Main : %s"%err)
