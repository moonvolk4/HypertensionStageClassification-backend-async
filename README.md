# Lab8 Async Service (Django)

Асинхронный сервис (порт `8001`) для отложенного вычисления `result_stage` по среднему АД.

## Что делает

- Принимает HTTP POST ` /calc ` с `id` заявки и давлением (`sys`, `dia`).
- Запускает «долгий расчёт» (задержка 5–10 секунд) в `ThreadPoolExecutor(max_workers=1)`.
- После завершения отправляет PUT в основной Go-сервис: `PUT http://localhost:8080/api/records/{id}/result`.
- Авторизация: сервис логинится как модератор (`POST /api/users/login`), кеширует JWT и шлёт `Authorization: Bearer <JWT>`.

## Формула

Среднее АД (MAP):

$$MAP = \frac{SYS + 2\cdot DIA}{3}$$

Дальше выбирается «стадия»:
- `MAP < 100` → `Стадия 1`
- `100 ≤ MAP < 120` → `Стадия 2`
- `MAP ≥ 120` → `Стадия 3`

(Если нужны другие пороги — скажи, поменяю.)

## Запуск

```bash
cd lab8_async_service_django
python -m venv env
. env/bin/activate
pip install -r requirements.txt

# JWT модератора для отправки результата в основной сервис
export MAIN_SERVICE_URL="http://localhost:8080"
export MODERATOR_USERNAME="moderator"
export MODERATOR_PASSWORD="moderator_password"

python manage.py runserver 0.0.0.0:8001
```

## Тест (Insomnia)

`POST http://localhost:8001/calc`

```json
{ "id": 123, "sys": 150, "dia": 95 }
```

Ответ придёт сразу `200 OK`, а обновление результата в основном сервисе произойдёт через 5–10 секунд.

## Callback формат

`PUT ${MAIN_SERVICE_URL}/api/records/{id}/result`

JSON (можно одно или оба поля):

```json
{ "result_map": 101.3, "result_stage": "Стадия 2" }
```
# HypertensionStageClassification-backend-async
