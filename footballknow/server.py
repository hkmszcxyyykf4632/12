"""Football Know API; private state is never mounted as static content."""
import os
import http.client
from datetime import datetime, timezone
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
from football.sync_control import SyncControlInput, read_control, set_control
from football import stock_analysis, stock_service, racing, racing_analysis
from football import horse_research


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
DEFAULT_ORIGINS = 'https://footballknow.art,https://www.footballknow.art,https://inwesting.shop,https://www.inwesting.shop'


def allowed_origins() -> set[str]:
    """Sites allowed to send changes; FOOTBALL_ALLOWED_ORIGINS lists a customer's own domains."""
    return {item.strip().rstrip('/') for item in os.environ.get('FOOTBALL_ALLOWED_ORIGINS', DEFAULT_ORIGINS).split(',') if item.strip()}


@app.middleware('http')
async def request_boundary(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method in {'POST','PUT','DELETE','PATCH'}:
        origin = request.headers.get('origin', '')
        try:
            parsed = urlsplit(origin)
        except ValueError:
            return JSONResponse({'detail':'请求来源格式不正确。'},status_code=403)
        approved = origin in allowed_origins()
        if os.environ.get('FOOTBALL_PRODUCTION') != '1':
            approved |= parsed.hostname in {'127.0.0.1','localhost','testserver'} and parsed.scheme in {'http','https'}
        if not approved:
            return JSONResponse({'detail':'请求来源不匹配，请从网站页面操作。'},status_code=403)
        length = request.headers.get('content-length', '0')
        if not length.isdigit() or int(length) > 64000:
            return JSONResponse({'detail':'请求内容过大。'},status_code=413)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path.endswith('.json'):
        # Snapshots are re-read every minute; revalidation answers unchanged files with 304.
        response.headers['Cache-Control'] = 'no-cache'
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


@app.get('/api/sync/control')
def get_sync_control(account: auth.Administrator = Depends(administrator)):
    return {**read_control(), 'worker': sync_status()}


@app.put('/api/sync/control')
def update_sync_control(value: SyncControlInput, account: auth.Administrator = Depends(administrator)):
    return set_control(value.enabled, account.username)


class StockWatchlistInput(BaseModel):
    codes: list[str] = Field(max_length=200)


@app.put('/api/stocks/watchlist')
def set_stock_watchlist(value: StockWatchlistInput, account: auth.Administrator = Depends(administrator)):
    from football.reviews import save_watchlist
    try:
        return save_watchlist(value.codes)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


def review_response(callback):
    try:
        return callback()
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (ValueError, ValidationError) as error:
        raise HTTPException(status_code=400, detail=str(error)[:240]) from None
    except (OSError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='复盘服务暂时无法连接，请稍后重试。') from None


@app.get('/api/reviews/football')
def get_football_review(match_id: str, league: LeagueId = 'epl'):
    from football.reviews import football_review
    return review_response(lambda: football_review(match_id, league))


@app.post('/api/reviews/football')
def create_football_review(match_id: str, league: LeagueId = 'epl', account: auth.Administrator = Depends(administrator)):
    from football.reviews import football_review
    return review_response(lambda: football_review(match_id, league, True))


@app.get('/api/stocks/{code}/review')
def get_stock_review(code: str):
    from football.reviews import stock_review
    return review_response(lambda: stock_review(code))


@app.post('/api/stocks/{code}/review')
def create_stock_review(code: str, account: auth.Administrator = Depends(administrator)):
    from football.reviews import stock_review
    return review_response(lambda: stock_review(code, True))


@app.get('/api/assets/{ident}/analysis')
def get_asset_analysis(ident: str):
    from football.reviews import asset_review
    return review_response(lambda: asset_review(ident))


@app.post('/api/assets/{ident}/analysis')
def create_asset_analysis(ident: str, account: auth.Administrator = Depends(administrator)):
    from football.reviews import asset_review
    return review_response(lambda: asset_review(ident, True))


@app.get('/api/analysis/protocols/info')
def get_protocol_info():
    from football.professional_prompts import protocol_metadata
    return protocol_metadata()


@app.get('/api/stocks/quotes')
def get_stock_quotes(codes: str):
    try:
        return stock_service.viewed_quotes(codes.split(','))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@app.get('/api/stocks/{code}/company')
def get_stock_company(code: str):
    try:
        return stock_service.detail(code, 'companies')
    except LookupError:
        raise HTTPException(status_code=404, detail='股票不存在。') from None


@app.get('/api/stocks/{code}/history')
def get_stock_history(code: str):
    try:
        return stock_service.detail(code, 'history')
    except LookupError:
        raise HTTPException(status_code=404, detail='股票不存在。') from None


@app.get('/api/stocks/{code}/analysis')
def get_stock_analysis(code: str):
    try:
        return stock_analysis.public_status(code)
    except LookupError:
        raise HTTPException(status_code=404, detail='这只股票不在当前港股名单内。') from None


@app.post('/api/stocks/{code}/analysis')
def create_stock_analysis(code: str, account: auth.Administrator = Depends(administrator)):
    try:
        return stock_analysis.generate(code)
    except LookupError:
        raise HTTPException(status_code=404, detail='股票不存在。') from None
    except ValidationError:
        raise HTTPException(status_code=400, detail='AI 返回的预测格式不正确，请稍后重试。') from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except (OSError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='股票分析服务暂时无法连接，请稍后重试。') from None


@app.get('/api/health')
def health(response: Response):
    """Machine-readable liveness for uptime monitors: 200 while the synchronizer heartbeat is fresh."""
    status = sync_status()
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(status['heartbeat'])).total_seconds()
    except (KeyError, TypeError, ValueError):
        age = None
    healthy = bool(status.get('running')) and age is not None and age < 120
    if not healthy:
        response.status_code = 503
    return {'status': ('paused' if status.get('paused') else 'ok') if healthy else 'degraded', 'paused': status.get('paused', False),
            'heartbeatAgeSeconds': None if age is None else round(age),
            'syncSeconds': status.get('syncSeconds'), 'summary': status.get('summary')}


@app.get('/api/match')
def match_detail(match_id: str, league: LeagueId = 'epl'):
    if len(match_id) > 200:
        raise HTTPException(status_code=422, detail='比赛编号格式不正确。')
    try:
        detail = get_detail(match_id, league, fetch_missing=read_control()['enabled'])
        if detail is None:
            raise HTTPException(status_code=503, detail='同步已暂停，本场尚无缓存资料。')
        return detail
    except LookupError:
        raise HTTPException(status_code=404, detail='比赛不存在。') from None
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='本场详细资料暂时无法更新，请稍后重试。') from None


@app.get('/api/racing/horses/{ident}')
def get_horse(ident: str):
    try:
        return racing.horse_detail(ident)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/racing/horses/{ident}/research')
def get_horse_research(ident: str):
    try:
        from datetime import datetime, timezone
        from football.racing_preparation import runner
        research = horse_research.get_research(ident)
        horse = racing.load(racing.FOLDER / 'horses' / (ident + '.json'))
        return {**research, 'preparation': runner({'id': ident, 'name': horse.get('name')}, horse,
                                                research, datetime.now(timezone.utc))}
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/racing/races/{ident}')
def get_racing_race(ident: str):
    try:
        return racing.get_race(ident)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/racing/races/{ident}/analysis')
def get_racing_analysis(ident: str):
    try:
        return racing_analysis.public_status(ident)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/racing/races/{ident}/pace')
def get_racing_pace(ident: str):
    from football.racing_pace import simulation
    try:
        return simulation(ident)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/racing/races/{ident}/preparation')
def get_racing_preparation(ident: str):
    from football.racing_preparation import assessment
    try:
        return assessment(ident, refresh=True)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.post('/api/racing/races/{ident}/analysis')
def create_racing_analysis(ident: str, phase: str, account: auth.Administrator = Depends(administrator)):
    try:
        return racing_analysis.generate(ident, phase)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except ValidationError:
        raise HTTPException(status_code=400, detail='AI 返回格式不完整，请重新生成。') from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except (OSError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='赛马分析暂时无法连接，请稍后重试。') from None


from football import videos, visits
from football import us_reference


@app.get('/api/reference/us/{ticker}/history')
def us_history(ticker: str):
    try:
        return us_reference.history(ticker)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


class VisitInput(BaseModel):
    event: str = Field(pattern=r'^[a-fA-F0-9-]{36}$')


@app.get('/api/visits')
def get_visits():
    return {'total': visits.counter()['total']}


@app.post('/api/visits')
def add_visit(value: VisitInput):
    try:
        return {'total': visits.counter(value.event)['total']}
    except ValueError:
        raise HTTPException(status_code=422, detail='访问编号不正确。') from None


@app.get('/api/admin/visits')
def admin_visits(account: auth.Administrator = Depends(administrator)):
    return visits.counter()


@app.get('/api/videos')
def get_videos():
    return videos.catalogue()


@app.get('/api/admin/videos')
def admin_videos(account: auth.Administrator = Depends(administrator)):
    return videos.catalogue(True)


@app.post('/api/admin/videos')
def add_video(value: videos.VideoInput, account: auth.Administrator = Depends(administrator)):
    try:
        return videos.save(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@app.put('/api/admin/videos/{ident}')
def edit_video(ident: str, value: videos.VideoInput, account: auth.Administrator = Depends(administrator)):
    try:
        return videos.save(value, ident)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/football-forecasts')
def football_forecast_index():
    from football.football_forecasts import read_index
    return read_index()


@app.get('/api/daily-football/{ident}/forecast')
def daily_football_forecast(ident: str):
    from football.football_forecasts import current_row, status
    try:
        return status(current_row(ident))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/daily-football/{ident}/research')
def daily_match_research(ident: str):
    from football.match_research import research
    try:
        return research(ident)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get('/api/match/research')
def centre_match_research(match_id: str, league: LeagueId = 'epl', include_detail: bool = False):
    from football.match_centre_research import get_research
    if len(match_id) > 200:
        raise HTTPException(status_code=422, detail='比赛编号格式不正确。')
    try:
        return get_research(match_id, league, include_detail)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        raise HTTPException(status_code=502, detail='本场分析资料暂时无法更新，请稍后重试。') from None


@app.get('/api/commodities/{ident}/history')
def commodity_history(ident: str):
    from football.commodity_history import history
    try:
        return history(ident)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


app.mount('/',StaticFiles(directory=str(PUBLIC),html=True),name='website')
