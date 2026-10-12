# API Aurevix Games
Базовый адрес backend, затем `/api`. OpenAPI JSON: `/openapi.json`, интерактивная документация `/docs`. Не путать REST с Gradio `/gradio`.

## Формат и авторизация
JSON; ошибки `{"error":{"code":"validation_error"}}`. Формат единый для HTTP/validation/unhandled errors. Коды локализуются frontend. Авторизация `Authorization: Bearer <opaque token>`; срок 24 часа. На сервере хранится SHA-256 token digest. Нет cookies, обязательной почты или клиентского поля admin. Logout отзывает текущую сессию; смена пароля отзывает все сессии.

| Метод | Путь | Назначение / права |
|---|---|---|
| POST | /auth/register | nickname,password; 201 + token,user |
| POST | /auth/login | nickname,password; token,user |
| POST | /auth/logout | текущая сессия |
| POST | /auth/password | old_password,new_password; вход |
| GET/PATCH | /me | профиль; PATCH принимает только bio |
| POST | /me/avatar | multipart file, вход; очищенный WebP |
| GET | /profiles/{id} | публичный профиль без admin |
| GET | /profiles/{id}/games | опубликованные игры автора |
| GET | /me/games | собственные игры и все версии |
| GET | /me/favorites | сохранённое избранное |
| GET | /games | q,genre,platform,tag,multiplayer,sort,page,limit |
| GET | /games/{id} | опубликованная игра и approved версии |
| PUT/DELETE | /games/{id}/favorite | вход; идемпотентно |
| PUT | /games/{id}/rating | вход; value 1..5 |
| POST | /games/upload | multipart; владелец/новая игра |
| GET | /versions/{id}/moderation | только владелец/admin; журнал |
| POST | /versions/{id}/resubmit | владелец; rejected/manual_review → pending |
| GET | /admin/moderation | admin; до 100 записей |
| POST | /admin/versions/{id} | admin; status,reason; публикация при approved |
| POST | /admin/games/{id}/block | admin; blocked,reason |
| GET | /admin/versions/{id}/inspection | admin; метаданные, hashes, текстовые образцы и журнал |
| GET | /admin/versions/{id}/archive | admin; скачать ZIP для изолированного ручного анализа |
| GET | /admin/audit | admin; до 100 событий |
| POST | /sdk/sessions | вход; game_id; 10-минутная игровая сессия |
| POST | /sdk/scores | вход; play_token,value; строго integer 0..1000000 |
| GET | /leaderboards | game_id опционально; до 50 лучших personal max |
| GET | /content/{game}/{version}/{path} | только approved и не blocked; sandbox CSP |
| GET | /media/{path} | WebP; только доступный опубликованный game/публичный avatar |

Каталог: сортировки new/popular/rating/updated; limit 1..24, default 12, page >=1. Ответ `{items,total,page,pages}`. Search ищет заголовки и описания на двух языках; пользовательские %/_ экранированы. Только approved current_version, не blocked. Ratings — сохранённые оценки, не выдуманные числа; при отсутствии рейтинг null.

Upload поля archive,icon,screenshot1,screenshot2,metadata (JSON string),game_id (необязателен для обновления). Meta: title_ru/en, description_ru/en, controls_ru/en, version, genres массив 1..3 из arcade/puzzle/action/racing/strategy/adventure, tags <=8 по 30 символов, platforms desktop/mobile, multiplayer boolean. UI выбирает один жанр; API допускает до трёх. ZIP <=20 MiB; распаковка <=80 MiB; <=600 файлов; ratio >150 для >1MiB файла отвергается; отдельный файл <=25 MiB. Иконка/скриншоты <=4 MiB каждое, <=16M pixels; перекодируются в WebP. SVG и server-executable файлы не принимаются. WASM бинарники вызывают ручной review. Никакого исполнения сервером.

Ограничения: global 180 req/min/IP; login 15/5min/IP + 8/5min/nickname; register 5/hour/IP; upload 4/hour/user; resubmit 3/hour/user; score 10/min/user. In-process, single worker; 429 при превышении. API с запрещённым Origin отдаёт 403; отсутствие Origin не заменяет проверки auth. OPTIONS с разрешённым Origin обрабатывает CORS middleware.

SDK не принимает user_id или game_id при отправке рекорда: game/account привязаны server-side к play_token. Одноразовый token поглощается атомарно; повтор запрещён. Результат **verified=false, competitive=false**: клиент всё ещё способен выдумать число в пределах bounds, поэтому не использовать для призов/соревнования. Общая таблица смешивает разные шкалы игр и предназначена только для демонстрации best personal score; meaningful global competitive scoring требует отдельной нормализации и verifier.

Статусы: pending,approved,rejected,manual_review. BackgroundTasks не durable queue. API может ответить pending до завершения анализа. При исчезновении процесса оператор должен восстановить pending через manual review/resubmit. Подробные payload schemas и validation constraints смотрите в OpenAPI.
