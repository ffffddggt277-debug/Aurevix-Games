# Aurevix Games — фактический отчёт проверки

## Итог и границы
Исходники и физический ZIP созданы. Портал запущен локально как production Next.js frontend + реальный FastAPI backend. **Не развёрнут в аккаунтах заказчика.** Весь backend рассчитан на один HF Space; постоянные данные — подключённый приватный том Hugging Face, без внешней БД/S3; клиент — Vercel.

This PUBLIC derivative excludes the actual backend/.env and contains no real API key. The previously delivered PRIVATE artifact had a requested key file. Не публиковать .env или весь ZIP в публичном репозитории. Значение ключа не включено в этот отчёт, screenshots, frontend или API schemas.

## Результаты
| Проверка | Статус | Подтверждение |
|---|---|---|
| Установка frontend зависимостей | Пройдено | npm install; package-lock.json |
| TypeScript | Пройдено | npm run typecheck, exit 0 |
| Линтер frontend | Пройдено | npm run lint, exit 0 |
| Production build | Пройдено | Next.js 16.4.0, npm run build, exit 0 |
| Frontend/SDK unit tests | Пройдено | 5 tests, 0 failures |
| npm audit | Пройдено | 0 reported vulnerabilities at time of check; не гарантия отсутствия всех уязвимостей |
| Python dependencies | Пройдено | pip install, pip check: No broken requirements |
| Backend/Gradio import | Пройдено | app.app FastAPI; mounted Gradio; app.py launches Uvicorn |
| Локальный запуск, health/OpenAPI | Пройдено | /health HTTP 200, OpenAPI exported to docs/openapi.json |
| Backend/security tests | Пройдено | 41 tests, 0 failures |
| Миграции на чистой БД | Пройдено | 001+002 applied during isolated API startup |
| Живые frontend-client integration tests | Пройдено | 13 checks; actual TypeScript API client, separate live API port 7861 and test DB |
| Браузерные сценарии | Пройдено | Chromium, main/catalog/search/empty state/forms/profile/favorites/upload/SDK/admin/localization/login/logout |
| Адаптивность | Пройдено | 390,768,1440 px; no detected horizontal overflow |
| Консоль и сеть | Пройдено | final browser-qa.json has zero console/page errors and zero unexpected HTTP failures |
| OpenRouter mocked edge cases | Пройдено | success,401,403,429,timeout,invalid JSON,response shape,missing key,invalid decision; fail-closed |
| Публичный список OpenRouter моделей | Пройдено | HTTP 200, inclusionai/ling-3.1-flash found |
| Реальный OpenRouter chat/completions | Пройдено | Provided key, requested model, HTTP 200, valid JSON decision approved; safe test metadata; one request |
| SQLite snapshot restore | Пройдено | local online-backup, digest validation and restore test |
| Секреты вне серверного .env | Пройдено | public archive scan finds no actual key |
| ZIP CRC + обязательные файлы | Пройдено | zipfile.testzip + required paths + screenshot presence; итоговая упаковка проверена отдельно |
| GitHub Actions workflow | Не запускалось | workflow supplied; local checks passed instead |
| Deployment в HF/Vercel | Не запускалось | no account login or deployment performed |
| Хранение после реального HF restart/rebuild | Требует проверки после развёртывания | bucket mount, read-write behavior, snapshot recovery and backups must be tested in the account |
| Реальный CORS/CSP/SDK на HTTPS deployed origins | Требует проверки после развёртывания | local versions tested; Production/Preview allowlist must match real origins |
| Нагрузочное тестирование / тысячи игроков | Не запускалось | no scaling guarantee |
| Онлайн-мультиплеер/WebSocket | Не запускалось | architecture/limitations documented; no room server implemented |
| ZeroGPU | Не запускалось | no local GPU-dependent function; remote OpenRouter and browser games do not require it |
| Threaded engine/SharedArrayBuffer/WebGPU compatibility | Не запускалось | game-specific validation required; worker/external network restricted |

Фактическая среда локального теста: Node 24.14.1, npm 11.11.0, Python 3.13.14, Linux. HF README targets Python 3.12, which must be checked during actual Space build.

## Что проверяли в backend
Auth registration/login/case-insensitive nickname uniqueness; password hashes; logout/revocation and expired/malformed tokens; profile ownership; admin field injection; CORS allowed and forbidden origins; brute-force limits; ZIP traversal, corrupted structure, file count/size, compression bomb, duplicate paths, symlinks and disallowed types; missing index.html; multipart upload; moderation failures; owner/admin isolation; version and metadata publication atomicity; favorites/rating persistence; game CSP and opaque-origin content; score bounds/user forgery/replay; game blocking/audit; admin inspection and ZIP download; chunked body cap; SQLite snapshot restore. The server did not execute game source.

## Честные ограничения реализации
- Submitted scores are explicitly unverified/noncompetitive. User/game binding and replay are protected, not arbitrary game rules. Global maxima across different score scales are informational only.
- No online multiplayer server is simulated. A multiplayer checkbox is only author-provided metadata; external game networking is blocked until a reviewed allowlist/protocol is added.
- Single process/writer; in-memory limits reset on restart; HF proxy IP behavior must be verified. No durable distributed moderation queue; orphan pending work requires manual recovery/resubmit.
- SQLite snapshots are appropriate for a small portal, not an untested high-scale service. Remote volume failures can leave an unconfirmed latest local commit; independent backups and recovery drills are mandatory.
- AI samples limited source and cannot guarantee malware detection. Large/binary projects require human review. Only sanitized game images are public; admin downloads untrusted source for isolated review.
- Dedicated third content origin is not implemented: Vercel frontend and HF backend are separate origins, with opaque sandbox+CSP for games.
- Actual bucket availability/pricing/quotas and Gradio/FastAPI proxy behavior remain account-specific. Ordinary Space disk is ephemeral.
- A private Space may require HF authorization and not be reachable as a public API. A key tracked in public Space Files cannot be made secret by .env naming or server headers.

## Реальные скриншоты
- `screenshots/01-home-desktop.png` — Главная, desktop 1440 px
- `screenshots/02-home-mobile.png` — Главная, mobile 390 px
- `screenshots/03-catalog-mobile.png` — Каталог, mobile 390 px
- `screenshots/04-home-tablet.png` — Главная, tablet 768 px
- `screenshots/05-catalog-desktop.png` — Каталог, desktop
- `screenshots/06-game-detail.png` — Страница игры
- `screenshots/07-game-player.png` — Работающий игровой iframe
- `screenshots/08-login.png` — Вход
- `screenshots/09-register.png` — Регистрация
- `screenshots/10-profile.png` — Тестовый профиль
- `screenshots/11-developer.png` — Панель разработчика
- `screenshots/12-publish-form.png` — Форма публикации
- `screenshots/13-moderation.png` — Реальный статус manual_review при отключённом ключе в тестовой среде
- `screenshots/14-sdk-documentation.png` — Документация SDK
- `screenshots/15-home-english.png` — English homepage
- `screenshots/16-publish-mobile.png` — Форма публикации, mobile English
- `screenshots/17-admin-moderation.png` — Защищённая очередь администратора

All screenshots use safe local test accounts. The manual_review screenshot intentionally tests missing-key fail-closed behavior in a test server; the separately configured real token was tested via an actual HTTPS completion. No real user data is seeded or distributed. Demo games are opt-in and marked; fresh installs have no fabricated ratings/records.

## Основные файлы
backend/app.py and backend/requirements.txt exist; backend/aurevix, backend/migrations/versions, backend/tests, backend/.env.example (placeholder only), backend/.env.example; frontend/src, package.json, package-lock.json; sdk/aurevix.js, aurevix.mjs, aurevix.d.ts; docs/API_RU.md, API_EN.md, SDK_RU.md, SDK_EN.md, openapi.json; DEPLOYMENT_GUIDE_RU.md; English guide; screenshots/; reports/; .gitignore and .github/workflows/ci.yml.

## Первые действия
1. Extract the PRIVATE ZIP and read PRIVATE_ARCHIVE_NOTICE_RU.md.
2. Run local backend/frontend using DEPLOYMENT_GUIDE_RU.md. app.py reads backend/.env by default.
3. Keep .env out of public GitHub/Space files; rotate the exposed key before production.
4. Create one HF backend Space and a private HF persistent volume; configure exact Vercel origin and storage.
5. Import frontend/ into Vercel, set NEXT_PUBLIC_API_URL to direct hf.space URL, redeploy, run post-deploy checklist.
