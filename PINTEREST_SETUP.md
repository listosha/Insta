# Pinterest автопубликация — настройка доступа (one-time)

Архитектура — зеркало Threads: cron-job.org → `workflow_dispatch` →
`publish-pinterest.yml` дренирует очередь `pinterest-schedule.json` через
Pinterest API v5 (`POST /v5/pins`), `refresh-pinterest-token.yml` продлевает
access-токен. Полный анализ: `pinterest-analysis-2026-06-01.md`.

> ⚠️ Главное про доступ: на **Trial**-доступе пины видны ТОЛЬКО автору (Sandbox).
> Публика их не увидит, пока приложение не апгрейднуто до **Standard** (ручная
> модерация, ~1–4 недели). Поэтому шаги 1–5 можно пройти сразу, а реально
> «включать» постинг (раскомментировать cron) — только после шага 6.

---

## Шаг 1. Бизнес-аккаунт Pinterest

API работает только с business-аккаунтом.
- Если аккаунт личный: pinterest.com → Settings → **Account management** →
  *Convert to a business account* (бесплатно, контент и подписчики сохраняются).
- Либо завести отдельный business-аккаунт под проект.

## Шаг 2. Зарегистрировать приложение

1. Зайти на **developers.pinterest.com/apps** под этим же аккаунтом.
2. **Connect app** → заполнить название (напр. `Pinterest Auto-Publisher`),
   описание, согласиться с Developer Guidelines.
3. После создания — **Manage** у приложения: там `App ID` и `App secret key`.
   Сохрани оба.
4. На вкладке **Configure** → секция **Redirect URIs** добавить РОВНО:
   ```
   http://localhost:8085/
   ```
   (это нужно для одноразового локального OAuth в шаге 3; со слэшем на конце).

## Шаг 3. Получить первый refresh-токен (локально, один раз)

Скрипт `tools/pinterest_oauth.py` поднимает локальный сервер на :8085,
открывает экран авторизации Pinterest, ловит редирект и обменивает код на токены.
Сторонних пакетов не нужно — только Python 3.

PowerShell (из корня репо):
```powershell
$env:PINTEREST_APP_ID="<App ID>"; $env:PINTEREST_APP_SECRET="<App secret>"; python tools/pinterest_oauth.py
```
Откроется браузер → **Allow** → в терминале появятся `access_token` (≈30 дней)
и `refresh_token` (≈60 дней, рефрешится бесконечно). Скопируй оба.

Запрашиваемые скоупы: `boards:read, boards:write, pins:read, pins:write`
(без `boards:write` пин не создаётся; `boards:read` — чтобы узнать `board_id`).

## Шаг 4. Узнать board_id целевой доски

Создай в интерфейсе Pinterest доску под проект (напр. «Питание и меню»), затем
получи её id (подставь свой access-токен):
```powershell
curl -H "Authorization: Bearer <ACCESS_TOKEN>" https://api.pinterest.com/v5/boards
```
Поле `id` нужной доски → впиши в `pinterest-schedule.json` (`board_id`) вместо
`REPLACE_WITH_BOARD_ID`.

## Шаг 5. GitHub Secrets

repo `listosha/Insta` → Settings → Secrets and variables → Actions:
- `PINTEREST_ACCESS_TOKEN`  = access_token из шага 3
- `PINTEREST_REFRESH_TOKEN` = refresh_token из шага 3
- `PINTEREST_APP_ID`        = App ID
- `PINTEREST_APP_SECRET`    = App secret
- `PINTEREST_REFRESH_PAT`   = fine-grained PAT с **Secrets: Read and write** на репо
  (нужен воркфлоу рефреша, чтобы перезаписать access-токен; отдельно от
  publish-PAT, у которого только Actions: R+W).

После этого можно прогнать `Publish Pinterest Pin` вручную (Actions → Run
workflow) — на Trial пин создастся, но будет виден только тебе (Sandbox). Это и
есть проверка, что токены/скрипт работают.

## Шаг 6. 🔴 Заявка Trial → Standard (чтобы пины видели все)

В Manage приложения — запрос на **Standard access**. Что подготовить:
1. **Публичная privacy policy.** В репо лежит `privacy-policy.md`. Опубликовать
   через **GitHub Pages**: Settings → Pages → Source = Deploy from a branch →
   `main` / root. Через пару минут policy доступна по
   `https://listosha.github.io/Insta/privacy-policy`. Эту ссылку — в заявку.
2. **Видео-демо OAuth-флоу** (частая причина отказа — «video does not show the
   authentication flow»). Записать экран, где видно ВСЮ цепочку:
   - экран авторизации Pinterest (тот, что открывает скрипт из шага 3);
   - нажатие **Allow**;
   - возврат и успешное получение токена (вывод скрипта в терминале);
   - один реальный вызов API — например создание пина (прогон воркфлоу или curl
     `POST /v5/pins`, видно ответ с `id` пина).
   Залить на YouTube (unlisted) / Drive, ссылку — в заявку.
3. Подтвердить соответствие Developer Guidelines.

Срок рассмотрения ~1–4 недели. **Только после одобрения Standard** имеет смысл
раскомментировать `schedule:` / включить триггер — до этого публика пинов не видит.

## Шаг 7. Когда Standard одобрен — включить автозапуск

1. В `publish-pinterest.yml` раскомментировать дневной `schedule:` cron как
   бэкстоп.
2. Основной триггер — cron-job.org → `workflow_dispatch` (как у Threads), тем же
   подходом и PAT с Actions: R+W:
   ```
   POST https://api.github.com/repos/listosha/Insta/actions/workflows/publish-pinterest.yml/dispatches
   Headers: Authorization: Bearer <PAT>, Accept: application/vnd.github+json, X-GitHub-Api-Version: 2022-11-28
   Body: {"ref":"main"}   → успех = HTTP 204
   ```
3. В `refresh-pinterest-token.yml` раскомментировать месячный `schedule:` cron.

> Держим число триггеров минимальным — частая автоматизация уже приводила к
> анти-абуз блокировке (см. память про suspension 2026-05-26).

## Обновление токенов

- **access-токен** (30 дней) — продлевает `refresh-pinterest-token.yml`
  автоматически (раз в месяц), перезаписывая `PINTEREST_ACCESS_TOKEN`.
- **refresh-токен** (60 дней) — Pinterest при рефреше может вернуть новый
  refresh_token; воркфлоу это логирует. Если вернул — обновить секрет
  `PINTEREST_REFRESH_TOKEN` вручную (или доработать воркфлоу на авто-перезапись).
  Запускать рефреш чаще раза в 60 дней, чтобы refresh-токен не протух.

## Контент (когда дойдём до наполнения очереди)

- Слайды переиспользуем из каруселей; идеал Pinterest — вертикаль **1000×1500
  (2:3)**, наши 1080×1350 тоже принимаются (ниже CTR).
- `title` ≤100 символов, `description` ≤500 (воркфлоу проверяет и падает при
  превышении). В описание — естественные ключевики (SEO), без medical-claims
  («лечит / вылечивает / гарантированное похудение»).
- `link` — кликабельная ссылка на лендинг (нативная фича Pinterest, чего нет в IG).
