# Безопасность и эксплуатационные границы

- Argon2id passwords; обязательная почта отсутствует. Никнеймы уникальны без учёта регистра, ASCII 3..24. Регистрация не принимает роль.
- 24h opaque tokens, hashed server-side, logout и password rotation revocation. Parent хранит собственный токен в sessionStorage; game iframe имеет opaque origin. XSS frontend всё равно опасен: не рендерить пользовательский HTML и не добавлять unsafe dependencies.
- Sandbox allow-scripts allow-pointer-lock, **без allow-same-origin**, без навигации/форм/popups/downloads. CSP применён даже при прямом открытии HTML. External connect/worker запрещены; локальные ассеты и WASM fetch permitted через self и CORS для public game files. CORS `*` разрешён только game content без credentials, не auth API.
- Игры физически находятся на backend origin, отдельно от Vercel frontend; более строгий dedicated content origin не реализован. API auth — только Bearer, не cookies. CSP API и iframe, nosniff, no-referrer, frontend permissions policy. CSP Next.js требует inline hydration/style, поэтому 'unsafe-inline' остаётся; nonce-based hardening возможно отдельно.
- ZIP bounded reads/expanded length/count/ratio/path normalization/duplicate/symlink/encryption/extension/entry checks. Stored under UUID game/version; no overwrites чужого контента. Никакого Python execution. Проверка CRC при чтении. Browser resource abuse и обфускация не решаются одним ZIP scanner.
- Иконки/скриншоты/аватары перекодируются через Pillow с pixel limits; SVG не используется.
- AI fail-closed structured decisions; ограниченная выборка исходников. Prompt injection рассматривается как риск: system-инструкция не абсолютная защита. AI не гарантирует антивирус. Бинарные/large projects → manual review.
- Admin only offline role grant + server checks; decisions/action audit persisted. Рабочая approved версия не заменяется pending. Обновлённые метаданные применяются только с одобрением.
- Scores user/game bound, one-time session, strict integer bounds; client can still fabricate a plausible score. Таблицы **unverified**. Подмена поля user_id запрещена, не заявляется полная защита от читов.
- Rate limits in process, one worker, no trust in forwarded IP. HF ingress может объединять IP; проверьте реальный deployment. Для серьёзной эксплуатации нужен доверенный ingress, shared limiter, anti-bot и мониторинг.
- SQLite + mounted volume snapshots — single writer. Не размещать live WAL на bucket. Backup integrity проверяется; нужна отдельная полная backup objects+db процедура. Нет distributed transactions, recovery после crash может потерять последнее не подтверждённое bucket обновление.
- Логи API не печатают тела, пароли или ключи; exception messages не отдаёт frontend. Не включать HTTP debug logging в production.

Автоматические тесты — часть защиты, не аудит. Не использовать проект как high-stakes competitive или массовый production service без review, нагрузочных и восстановительных тестов.
