# Карта воронки Instagram -> приложение (05.06.2026)

Связка: Reels (охват) -> коммент-триггер / BotHelp -> авто-DM с deep-link -> нужный экран приложения.
Источник схемы ссылок: `miniapp/docs/instagram-funnel-deeplinks.md`.

## Формула ссылки (для Instagram - web-форма)

```
https://app.listoshenkov.ru/?section=PARAM
```

Web-форма открывается без Telegram, роутер внутри сам раскрывает экран.
Проверка перед публикацией: тот же URL на `https://dev.listoshenkov.ru/?section=PARAM`.
Аналитика переходов пишется автоматически: событие `deep_link` + `section_open`, поле `referrer = PARAM`.

## Гейт лид-магнитов (решено 06.06.2026)

Бесплатные гайды (`freeguide_*`) гейтим на **email** по схеме **тизер → гейт**: показываем начало гайда (первые пункты, видно пользу) → дальше форма «куда прислать протокол» (одно поле, email) → после ввода открывается целиком. Цель — захват холодного трафика с рилсов в базу. Минимум трения: одно поле, формулировка про доставку, не «регистрация».

✅ ГОТОВО И ПРОВЕРЕНО 06.06.2026: гейт живой на обоих гайдах — `protokol-zhelezo-8-nedel` и `protokol-volosy-3-mesyaca`.

## Принцип: матчим температуру

- Холодный (с рилса) -> бесплатное, низкий порог (гайд, эфир, игра). Цель - захват в базу по email.
- Тёплый (в приложении / email) -> консультация, анализы, БАД-комиссия.
- Горячий (после консультации) -> меню, курсы, Гайды Pro.

Железодефицит - двигатель охвата (пост #2 это доказал). Меню и курсы - апсейлы, не лобовая продажа с рилса.

---

## Карта: рилс -> ключевое слово -> точный URL

| Рилс (боль) | Ключевое слово (BotHelp) | PARAM | Точный URL | Температура |
|---|---|---|---|---|
| 1. Анализы в норме, а ты разбитая | `СХЕМА` | `freeguide_protokol-zhelezo-8-nedel` | https://app.listoshenkov.ru/?section=freeguide_protokol-zhelezo-8-nedel | холодный, лид-магнит |
| 2. ТТГ в норме, симптомы есть | `ЩИТОВИДКА` | `ephir_17` | https://app.listoshenkov.ru/?section=ephir_17 | холодный, эфир «Железо на нуле, а щитовидка тормозит» |
| 3. 5 ошибок, ферритин стоит | `СХЕМА` | `freeguide_protokol-zhelezo-8-nedel` | https://app.listoshenkov.ru/?section=freeguide_protokol-zhelezo-8-nedel | холодный, лид-магнит — обещанный протокол (сколько держать + как закрыть депо), email-gated. ИСПРАВЛЕНО: было posts_iron (подборка постов) = не совпадало с обещанием в озвучке |
| 4. Омепразол ворует железо | `ВРАГИ` | `game_iron` (+ `pills_iron`) | https://app.listoshenkov.ru/?section=game_iron | интерактив-шеринг + комиссия |
| 5. Сплю 8 часов, не высыпаюсь | `ЭНЕРГИЯ` | `freeguide_protokol-zhelezo-8-nedel` | https://app.listoshenkov.ru/?section=freeguide_protokol-zhelezo-8-nedel | холодный, широкий |

### Запасные хуки (под будущие рилсы)

| Боль | Слово | PARAM | URL |
|---|---|---|---|
| Выпадение волос | `ВОЛОСЫ` | `freeguide_protokol-volosy-3-mesyaca` | https://app.listoshenkov.ru/?section=freeguide_protokol-volosy-3-mesyaca |
| Что принимать (БАД-комиссия) | `ЖЕЛЕЗО` | `pills_iron` | https://app.listoshenkov.ru/?section=pills_iron |
| Готов разобраться (горячий) | `РАЗБОР` | `consultation` | https://app.listoshenkov.ru/?section=consultation |
| Скидка на анализы | `АНАЛИЗЫ` | `discount` | https://app.listoshenkov.ru/?section=discount |

---

## Справочник PARAM (из deeplinks-доки)

Фиксированные: `free`, `pills` (умеет `&q=Магний`), `consultation`, `menu`, `courses`/`course` (Гормональный баланс), `weight`/`course_weight` (Управление весом), `discount`, `quiz`, `games`, `game_iron`.
Готовые ярлыки по железу: `pills_iron`, `posts_iron`, `freeguide_protokol-zhelezo-8-nedel`, `freeguide_protokol-volosy-3-mesyaca`.
С id: `freeguide_<slug>`, `guide_<slug>`, `post_<id>`, `supp_<id>`, `podcast_<id>`, `ephir_<id>`, `game_<slug>`.

Слаги бесплатных гайдов (`free-guides/catalog.json`): `protokol-zhelezo-8-nedel`, `protokol-volosy-3-mesyaca`, `gaid-gormonalnyj-balans`, `gaid-kbzhu`, `gaid-ves-v-zaschite`, `50-sovetov-pohudeniya`, `fodmap-spisok-produktov` (+ скрытые `fodmap-menu-7-dnej`, `metodichka-schitovidnaya`).

---

## Логика бота (BotHelp)

Один бот, ветка по ключевому слову. На каждое слово:
1. Триггер: комментарий под рилсом содержит слово (+ дубль-триггер: то же слово в директе).
2. Авто-DM: цепляющая фраза + кнопка с точным URL из таблицы.
3. Тег на контакт (напр. `reels-схема`, `reels-враги`) - для подсчёта лидов и догрева.
4. Опционально: через 1 день догрев-сообщение тёплым (кейс / приглашение на консультацию).

## Атрибуция (чтобы решать по деньгам, не по ощущению)

- **Источник (какой рилс дал лидов):** счётчик срабатываний ключевого слова в BotHelp. Поэтому у каждого рилса - своё слово.
- **Что открыли в приложении:** событие `deep_link` / `referrer = PARAM` в `analytics_events`.
- Связка двух даёт полную картину: рилс -> сколько написали слово -> сколько открыли экран -> сколько дошли до покупки/консультации.
- Если два рилса ведут на один PARAM (1 и 5 -> гайд железа), различай их по разным ключевым словам в BotHelp.

## Открытые вопросы

- Скидка на анализы: `?section=discount` ведёт в общий раздел скидок; если нужна именно страница Invitro - уточнить отдельный PARAM.
- Курсы «Гормональный баланс» / «Управление весом» и «Меню» - апсейлы, под них нужны свои топ-хуки позже (связка «не худеешь при убитом ферритине» красиво мостит железо -> вес).
