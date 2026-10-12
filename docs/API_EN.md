# Aurevix REST API
Base URL: direct backend origin + `/api`; OpenAPI `/openapi.json`, Swagger `/docs`.
Errors: `{"error":{"code":"..."}}`. Auth: Bearer opaque token, 24h lifetime, server-side digest, current-session logout and all-session revocation on password change. Registration never accepts roles. No required email.

Endpoints (exact payload schemas in OpenAPI):
- POST /auth/register, /auth/login: nickname,password.
- POST /auth/logout; POST /auth/password: old_password,new_password.
- GET/PATCH /me (bio only); POST /me/avatar (multipart file).
- GET /profiles/{id}, /profiles/{id}/games, /me/games, /me/favorites.
- GET /games: q,genre,platform,tag,multiplayer,sort,page,limit; response items,total,page,pages. Sort new/popular/rating/updated; limit <=24. Only published/unblocked games.
- GET /games/{id}; PUT/DELETE /games/{id}/favorite; PUT /games/{id}/rating: value 1..5.
- POST /games/upload: multipart archive,icon,screenshot1,screenshot2,metadata JSON string, optional game_id.
- GET /versions/{id}/moderation (owner/admin); POST /versions/{id}/resubmit (owner).
- GET /admin/versions/{id}/inspection: metadata, file list/hashes, bounded samples and moderation log; GET /admin/versions/{id}/archive: download ZIP for isolated review.
- GET /admin/moderation, /admin/audit; POST /admin/versions/{id}: status,reason; POST /admin/games/{id}/block: blocked,reason. Admin only.
- POST /sdk/sessions: game_id (authenticated); POST /sdk/scores: play_token,value (integer 0..1000000); GET /leaderboards with optional game_id.
- GET /content/{game}/{version}/{path}, /media/{path}: public approved content with isolation headers.

Upload metadata: title_ru/en,description_ru/en,controls_ru/en,version,genres 1..3 from arcade/puzzle/action/racing/strategy/adventure,tags <=8x30,platforms desktop/mobile,multiplayer. ZIP <=20MiB, expanded <=80MiB, <=600 files, <=25MiB per file, suspicious compression ratios rejected; root index.html required. Images <=4MiB and 16M pixels; re-encoded WebP. No SVG/server scripts. Version metadata is applied only after approval.

Status pending/approved/rejected/manual_review; OpenRouter failures never approve. BackgroundTasks is not durable; crashed pending requires operator action. Admin queue/history and owned/favorite lists have 100-record caps. Leaderboards cap 50 personal maxima and explicitly return verified=false,competitive=false. Global maxima across unrelated game scales are informational only. A play token is account/game-bound and atomically single-use; arbitrary game results still cannot be trusted.

Limits: 180 requests/min/IP global; login 15/5min/IP and 8/5min/nickname; registration 5/hour/IP; upload 4/hour/user; resubmit 3/hour/user; scores 10/min/user. Single-process limiter, not a distributed abuse system. Exact origin allowlist; forbidden Origin →403, credentials still required regardless of CORS.
