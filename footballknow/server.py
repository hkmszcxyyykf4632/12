"""Football Know API; private state is never mounted as static content."""
import os
import http.client
import socket
import ssl
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, SecretStr, ValidationError

from football import ai, auth
from football.analysis import analyze_next
from football.evaluation import evaluation_status
from football.files import PUBLIC, read_json
from football.leagues import LeagueId
from football.match_details import get_detail, next_lineup_evidence


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: SecretStr = Field(min_length=1, max_length=256)


class PasswordInput(BaseModel):
    current: SecretStr = Field(min_length=1, max_length=256)
    replacement: SecretStr = Field(min_length=12, max_length=256)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    auth.initialize_database()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def request_boundary(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method in {'POST','PUT','DELETE','PATCH'}:
        origin = request.headers.get('origin', '')
        try:
            parsed = urlsplit(origin)
        except ValueError:
            return JSONResponse({'detail':'请求来源格式不正确。'},status_code=403)
        approved = origin in {'https://footballknow.art','https://www.footballknow.art'}
        if os.environ.get('FOOTBALL_PRODUCTION') != '1':
            approved |= parsed.hostname in {'127.0.0.1','localhost','testserver'} and parsed.scheme in {'http','https'}
        if not approved:
            return JSONResponse({'detail':'请求来源不匹配，请从网站页面操作。'},status_code=403)
        length = request.headers.get('content-length', '0')
        if not length.isdigit() or int(length) > 64000:
            return JSONResponse({'detail':'请求内容过大。'},status_code=413)
    response = await call_next(request)
    if request.url.path.startswith('/api/') or request.url.path.endswith('.json'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse({'detail':'输入格式不正确，请检查字段长度和格式。'}, status_code=422)


def administrator(request: Request) -> auth.Administrator:
    account = auth.current_admin(request.cookies.get('fk_session'))
    if account is None:
        raise HTTPException(status_code=401,detail='请先登录管理员账号。')
    return account


@app.get('/api/auth/me')
def whoami(request: Request):
    account = auth.current_admin(request.cookies.get('fk_session'))
    return {'authenticated':account is not None,'username':account.username if account else None}


@app.post('/api/auth/login')
def sign_in(credentials: LoginInput, response: Response):
    result = auth.login(credentials.username,credentials.password.get_secret_value())
    if result is None:
        raise HTTPException(status_code=401,detail='账号或密码不正确；多次失败后请等十分钟再试。')
    account, token = result
    response.set_cookie('fk_session',token,max_age=auth.SESSION_SECONDS,httponly=True,
                        secure=os.environ.get('FOOTBALL_PRODUCTION')=='1',samesite='strict',path='/')
    return {'authenticated':True,'username':account.username}


@app.post('/api/auth/logout')
def sign_out(request: Request, response: Response):
    auth.logout(request.cookies.get('fk_session',''))
    response.delete_cookie('fk_session',path='/')
    return {'ok':True}


@app.post('/api/auth/password')
def update_password(credentials: PasswordInput, account: auth.Administrator = Depends(administrator)):
    if not auth.change_password(account,(credentials.current.get_secret_value(),credentials.replacement.get_secret_value())):
        raise HTTPException(status_code=400,detail='当前密码不正确。')
    return {'ok':True,'message':'密码已更新，请重新登录。'}


@app.get('/api/ai/settings')
def get_ai_settings(account: auth.Administrator = Depends(administrator)):
    return ai.public_settings()


@app.put('/api/ai/settings')
def set_ai_settings(incoming: ai.AISettings, account: auth.Administrator = Depends(administrator)):
    try:
        return ai.save_settings(incoming)
    except (ValueError,OSError) as error:
        raise HTTPException(status_code=400,detail=str(error)) from None


@app.get('/api/analysis/rules')
def get_rules(account: auth.Administrator = Depends(administrator)):
    return {'text':ai.analysis_rules()}


@app.put('/api/analysis/rules')
def set_rules(rules: ai.RuleText, account: auth.Administrator = Depends(administrator)):
    ai.save_rules(rules)
    return {'ok':True}


@app.get('/api/analysis/{team_id}')
def next_analysis(team_id: int, league: LeagueId = 'epl'):
    try:
        report = analyze_next(team_id, league)
        cached = ai.cached_analysis(team_id, league)
        return {'report':report,'ai':cached,'aiMatchesNext':bool(cached and report.match and cached.fixtureId==report.match.id),
                'evaluation':evaluation_status(league), 'lineupEvidence':next_lineup_evidence(league,report.match)}
    except LookupError:
        raise HTTPException(status_code=404,detail='球队不存在。') from None


@app.post('/api/analysis/{team_id}')
def run_analysis(team_id: int, league: LeagueId = 'epl', account: auth.Administrator = Depends(administrator)):
    try:
        return ai.generate_analysis(team_id, league)
    except (ValueError,ValidationError) as error:
        raise HTTPException(status_code=400,detail='AI 服务返回内容格式不正确。' if isinstance(error,ValidationError) else str(error)) from None
    except LookupError:
        raise HTTPException(status_code=404,detail='球队不存在。') from None
    except (OSError,socket.timeout,ssl.SSLError,http.client.HTTPException):
        raise HTTPException(status_code=502,detail='暂时无法连接 AI 服务，请稍后重试。') from None


@app.get('/api/status')
def sync_status():
    path = PUBLIC / 'sync-status.json'
    return read_json(path) if path.exists() else {'running':False,'jobs':{},'message':'后台同步服务尚未启动。'}


@app.get('/api/match')
def match_detail(match_id: str, league: LeagueId = 'epl'):
    if len(match_id) > 200:
        raise HTTPException(status_code=422, detail='比赛编号格式不正确。')
    try:
        return get_detail(match_id, league)
    except LookupError:
        raise HTTPException(status_code=404, detail='比赛不存在。') from None
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='本场详细资料暂时无法更新，请稍后重试。') from None


app.mount('/',StaticFiles(directory=str(PUBLIC),html=True),name='website')
