# Aurevix Games — Public setup

# Public: 7 шагов
1. Создайте Public GitHub-репозиторий и загрузите AUREVIX_GAMES_PUBLIC.zip. Не загружайте старый PRIVATE ZIP с токеном.
2. Добавьте отдельно .github/workflows/unpack.yml из приложенного файла. Settings -> Actions -> General -> Workflow permissions -> Read and write. Actions -> Unpack Aurevix project -> Run workflow. Исходники появятся в корне, frontend будет готов для Vercel.
3. Создайте один Public Hugging Face Space: Gradio, Blank, CPU Basic. Загрузите только app.py и requirements.txt из space-bootstrap/ в корень Space. app.py сам скачивает backend из публичного ZIP.
4. В HF Settings добавьте Secret OPENROUTER_API_KEY с вашим токеном. Variables: PROJECT_ZIP_URL=https://raw.githubusercontent.com/ВАШ_ЛОГИН/ВАШ_РЕПОЗИТОРИЙ/main/AUREVIX_GAMES_PUBLIC.zip; OPENROUTER_MODEL=inclusionai/ling-3.1-flash. Токен автоматически записывается в серверный runtime .env, а не в публичные исходники.
5. В Vercel импортируйте GitHub-репозиторий. Root Directory=frontend, Framework=Next.js, NEXT_PUBLIC_API_URL=https://ВАШ-SPACE.hf.space (без /api). Нажмите Deploy.
6. В HF задайте FRONTEND_URL=https://ВАШ-САЙТ.vercel.app и перезапустите Space. Для постоянных данных подключите приватный read-write том HF; задайте DATA_DIR=/tmp/aurevix-runtime и PERSISTENT_DIR=/mnt/aurevix (фактический путь тома). Проверьте восстановление, затем APP_ENV=production и PERSISTENCE_CONFIRMED=yes.
7. Откройте https://ВАШ-SPACE.hf.space/health и сайт Vercel; проверьте регистрацию и каталог.

Проверено локально: workflow Python extraction, запуск backend из ZIP, health/OpenAPI HTTP 200, создание runtime .env. В аккаунтах заказчика GitHub Actions/HF/Vercel не запускались. Ключ и модель отдельно проверены реальным OpenRouter запросом HTTP 200. Public ZIP не содержит настоящий ключ. Обычный диск HF Space временный; без подключённого постоянного тома данные могут пропасть после restart/rebuild. Изменение NEXT_PUBLIC_API_URL требует Redeploy Vercel. Полный исходный backend остаётся в backend/, но для простой загрузки из ZIP используйте два файла из space-bootstrap/.
