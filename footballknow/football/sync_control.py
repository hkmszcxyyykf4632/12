"""An administrator's persistent pause switch, shared by web and worker processes."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, StrictBool

from .files import STATE, publish, read_json


class SyncControlInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: StrictBool


def control_path():
    return STATE / 'sync-control.json'


def read_control():
    try:
        value = read_json(control_path())
        if not isinstance(value.get('enabled'), bool):
            raise ValueError('Invalid pause state')
        return {'enabled': value['enabled'], 'changedAt': value.get('changedAt'), 'changedBy': value.get('changedBy')}
    except FileNotFoundError:
        return {'enabled': True, 'changedAt': None, 'changedBy': None}
    except (OSError, ValueError, AttributeError):
        return {'enabled': False, 'changedAt': None, 'changedBy': None, 'message': '同步开关资料读取失败，暂时停止抓取。'}


def set_control(enabled, username):
    value = {'enabled': enabled, 'changedAt': datetime.now(timezone.utc).isoformat(), 'changedBy': username}
    publish(control_path(), value)
    return value
