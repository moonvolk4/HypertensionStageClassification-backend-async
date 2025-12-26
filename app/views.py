import random
import time
import os
import threading
from concurrent import futures

import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

MAIN_SERVICE_URL = os.environ.get('MAIN_SERVICE_URL', 'http://localhost:8080').rstrip('/')
MODERATOR_USERNAME = os.environ.get('MODERATOR_USERNAME', '').strip()
MODERATOR_PASSWORD = os.environ.get('MODERATOR_PASSWORD', '').strip()

_token_lock = threading.Lock()
_moderator_token: str | None = None

executor = futures.ThreadPoolExecutor(max_workers=1)


def _extract_token(payload: dict) -> str | None:
    for key in ('token', 'access_token', 'access', 'jwt'):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # sometimes backend returns {"data": {"token": "..."}}
    data = payload.get('data')
    if isinstance(data, dict):
        for key in ('token', 'access_token', 'access', 'jwt'):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def get_moderator_token(force_refresh: bool = False) -> str | None:
    global _moderator_token
    if not MODERATOR_USERNAME or not MODERATOR_PASSWORD:
        return None

    with _token_lock:
        if _moderator_token and not force_refresh:
            return _moderator_token

        try:
            resp = requests.post(
                f"{MAIN_SERVICE_URL}/api/users/login",
                json={'login': MODERATOR_USERNAME, 'password': MODERATOR_PASSWORD},
                timeout=5,
            )
            if resp.status_code >= 400:
                return None
            payload = resp.json() if resp.content else {}
            if not isinstance(payload, dict):
                return None
            token = _extract_token(payload)
            if not token:
                return None
            _moderator_token = token
            return _moderator_token
        except requests.RequestException:
            return None


def calc_map(sys_value: float | None, dia_value: float | None) -> float | None:
    if sys_value is None or dia_value is None:
        return None
    return (sys_value + 2.0 * dia_value) / 3.0


def calc_stage(sys_value: float | None, dia_value: float | None) -> str:
    map_value = calc_map(sys_value, dia_value)
    if map_value is None:
        # If pressure is missing, still write a deterministic value
        return 'Стадия 1'
    if map_value < 100:
        return 'Стадия 1'
    if map_value < 120:
        return 'Стадия 2'
    return 'Стадия 3'


def long_task(record_id: int, sys_value: float | None, dia_value: float | None) -> dict:
    time.sleep(random.randint(5, 10))
    result_map = calc_map(sys_value, dia_value)
    return {
        'id': record_id,
        'result_map': result_map,
        'result_stage': calc_stage(sys_value, dia_value),
    }


def put_result(record_id: int, result_map: float | None, result_stage: str) -> None:
    token = get_moderator_token(force_refresh=False)
    if not token:
        return

    url = f"{MAIN_SERVICE_URL}/api/records/{record_id}/result"
    body: dict = {'result_stage': result_stage}
    if result_map is not None:
        body['result_map'] = float(result_map)

    def _do_put(jwt: str) -> requests.Response:
        return requests.put(
            url,
            json=body,
            headers={
                'Authorization': f'Bearer {jwt}',
                'Content-Type': 'application/json',
            },
            timeout=5,
        )

    try:
        resp = _do_put(token)
        if resp.status_code == 401:
            refreshed = get_moderator_token(force_refresh=True)
            if refreshed:
                _do_put(refreshed)
    except requests.RequestException:
        return


def result_callback(task: futures.Future):
    try:
        result = task.result()
    except futures._base.CancelledError:
        return

    record_id = result.get('id')
    result_stage = result.get('result_stage')
    result_map = result.get('result_map')
    if not record_id or not result_stage:
        return

    put_result(int(record_id), result_map, str(result_stage))


@api_view(['POST', 'OPTIONS'])
def calc(request):
    if 'id' not in request.data:
        return Response({'error': 'id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        record_id = int(request.data['id'])
    except (ValueError, TypeError):
        return Response({'error': 'bad id'}, status=status.HTTP_400_BAD_REQUEST)

    sys_value = request.data.get('sys')
    dia_value = request.data.get('dia')

    try:
        sys_value = float(sys_value) if sys_value is not None else None
    except (ValueError, TypeError):
        sys_value = None

    try:
        dia_value = float(dia_value) if dia_value is not None else None
    except (ValueError, TypeError):
        dia_value = None

    task = executor.submit(long_task, record_id, sys_value, dia_value)
    task.add_done_callback(result_callback)

    return Response(status=status.HTTP_200_OK)
