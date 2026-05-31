# Threads автопубликация — настройка

Зеркало инстаграмной механики, но для текстовых постов в Threads.
Очередь: `threads-schedule.json`. Воркфлоу: `.github/workflows/publish-threads.yml`.

## Что делает движок

`publish-threads.yml` при запуске берёт самую раннюю запись со `status: "pending"`,
чей слот уже наступил (по Москве), публикует её текстом в Threads и помечает
`published`. Один пост за запуск — как у каруселей. До слота не публикует, так что
задержавшийся запуск может только опоздать, но не выстрелить раньше времени.

## Формат записи в `threads-schedule.json`

```json
{
  "id": 1,
  "date": "2026-06-02",
  "time": "12:00",
  "timezone": "Europe/Moscow",
  "text": "Текст поста, до 500 символов. Первая строка - хук.",
  "status": "pending"
}
```

После публикации движок дописывает `thread_id` и `published_at`.
Жёсткий лимит Threads - **500 символов** на пост (воркфлоу проверяет и падает, если больше).

## Шаги настройки (твоя сторона, одноразово)

Токен для Threads - **отдельный** от инстаграмного (другой граф: `graph.threads.net`).

1. **Meta app.** В том же приложении Meta, что используется для IG, добавь
   use-case **Threads API** (отдельное приложение создавать не нужно).
   Права: `threads_basic` + `threads_content_publish`.
2. **OAuth → короткий токен → длинный токен (60 дней).**
   - Короткий: пройди OAuth-флоу Threads, получи `access_token`.
   - Обменяй на длинный:
     `GET https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=<APP_SECRET>&access_token=<SHORT_TOKEN>`
   - В ответе - `access_token` на 60 дней.
3. **Узнай свой Threads user id:**
   `GET https://graph.threads.net/v1.0/me?fields=id,username&access_token=<LONG_TOKEN>`
   Поле `id` - это `THREADS_USER_ID`.
4. **GitHub secrets** (repo `listosha/Insta` → Settings → Secrets and variables → Actions):
   - `THREADS_ACCESS_TOKEN` = длинный токен из шага 2.
   - `THREADS_USER_ID` = id из шага 3.
5. **Первый запуск вручную.** Положи в `threads-schedule.json` один тестовый
   пост с прошедшим слотом, запусти `Publish Threads Post` через
   Actions → Run workflow. Убедись, что пост появился в Threads и запись стала
   `published`.

## Когда заработало - включить автозапуск

Триггер тот же, что у каруселей: **cron-job.org → workflow_dispatch**, тем же
PAT (у него уже есть Actions: Read+write на репо). Добавь на cron-job.org
задания на:

```
POST https://api.github.com/repos/listosha/Insta/actions/workflows/publish-threads.yml/dispatches
Headers: Authorization: Bearer <PAT>, Accept: application/vnd.github+json, X-GitHub-Api-Version: 2022-11-28
Body: {"ref":"main"}   → успех = HTTP 204
```

Слоты под Threads (предложение, скорректируй): **12:00 и 18:00 МСК** - 2 поста/день,
отдельно от инстаграмных слотов, чтобы не наслаивать триггеры. При желании можно
раскомментировать `schedule:` в воркфлоу как ежедневный бэкстоп (21:00 МСК).

> Держим число триггеров минимальным - частая автоматизация уже приводила к
> анти-абуз блокировке аккаунта (см. память про suspension 2026-05-26).

## Обновление токена (раз в ~50 дней)

Длинный токен живёт 60 дней. Обновляется так:
`GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=<LONG_TOKEN>`

Варианты:
- **Вручную:** раз в ~50 дней дёрнуть запрос, обновить secret `THREADS_ACCESS_TOKEN`.
- **Автоматически:** воркфлоу `refresh-threads-token.yml` (см. рядом) - дёргает
  refresh и перезаписывает secret через GitHub API. Нужен дополнительный PAT с
  правом `secrets: write` в secret `THREADS_REFRESH_PAT`. Включать после того,
  как публикация заработает.
