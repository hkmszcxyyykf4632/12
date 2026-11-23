"""Same-origin private watchlist endpoints; pairing is user initiated."""
import os
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from . import stock_following as store

router = APIRouter(prefix='/api/stocks/following')
COOKIE = 'fy_stock_device'


class Change(BaseModel):
    id: UUID
    code: str = Field(pattern=r'^\d{5,6}$')
    following: bool


class Changes(BaseModel):
    changes: list[Change] = Field(max_length=200)


class PairInput(BaseModel):
    code: str = Field(min_length=12, max_length=30)


def _run(action):
    try:
        return action()
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@router.get('')
def read(request: Request, response: Response):
    state, token = store.connect(request.cookies.get(COOKIE))
    response.set_cookie(COOKIE, token, max_age=31536000, httponly=True,
                        secure=os.environ.get('FOOTBALL_PRODUCTION') == '1', samesite='strict', path='/')
    return state


@router.post('')
def change(value: Changes, request: Request):
    return _run(lambda: store.apply(request.cookies.get(COOKIE), [c.model_dump(mode='json') for c in value.changes]))


@router.post('/pair')
def pair(request: Request):
    return _run(lambda: store.make_pair(request.cookies.get(COOKIE)))


@router.post('/join')
def join(value: PairInput, request: Request):
    return _run(lambda: store.join_pair(request.cookies.get(COOKIE), value.code))
