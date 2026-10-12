# Aurevix SDK v1

## Подключение
Включите `sdk/aurevix.js` в ZIP игры, рядом с index.html. Платформа добавляет `?platformOrigin=...` к iframe URL. SDK проверяет source родителя и точный origin. Для стороннего embedding передайте parentOrigin явно; '*' при отправке запросов не используется.

```html
<script src="aurevix.js"></script>
<script>
(async () => {
  const sdk = new AurevixSDK('ID_ВАШЕЙ_ИГРЫ');
  try {
    const info = await sdk.init();
    if (!info.authenticated) return;
    const result = await sdk.submitScore(120);
    console.log(result.verified); // false — не соревновательный рекорд
    const board = await sdk.getLeaderboard();
    console.log(board.items);
  } catch (error) {
    console.warn(error.code); // unauthorized, timeout, invalid_score и др.
  }
})();
</script>
```

Для module/TypeScript скопируйте также aurevix.mjs:
```typescript
import { AurevixSDK } from './aurevix.mjs';
const sdk = new AurevixSDK('game-id', { parentOrigin: 'https://your-project.vercel.app' });
const state = await sdk.init();
const board = await sdk.getLeaderboard();
// При завершении/размонтировании:
sdk.destroy();
```
Type definitions: aurevix.d.ts (при необходимости сопоставьте declaration для .mjs в своём bundler). Global browser script не требует npm или CDN.

Методы: init(),submitScore(integer 0..1_000_000),getLeaderboard(),destroy(). У запросов 10-секундный timeout; не более 10 ожидающих. source/origin/channel/id проверяются. Ошибки: invalid_parent_origin,not_embedded,invalid_score,timeout,too_many_requests,unauthorized,invalid_play_session,destroyed,request_failed.

Платформа принимает сообщения только от contentWindow текущего opaque iframe. gameId init должен совпадать с игрой страницы. SDK не получает API session token или play_token: доверенный parent сам создаёт игровую сессию и отправляет результат с текущим аккаунтом. Вторая отправка в той же play session запрещена; нажмите Restart для нового прохождения. Сервер не принимает user_id, чужой play token и повторный score. Не вызывайте API напрямую из sandbox.

## Честная граница античита
Браузерный код нельзя считать источником истинного результата. SDK защищает привязку пользователя, game id, тип/диапазон и replay, но **не доказывает победу**. Все записи непроверенные и исключены из соревновательной интерпретации. Для настоящего состязания нужен собственный authoritative server verifier: последовательность команд, seed, правила, тайминг, replay validation. Такой универсальный verifier не может честно существовать для произвольных загружаемых JS-игр.

SDK тесты находятся frontend/tests/sdk.test.mjs; server tests — backend/tests; живой API client integration — frontend/tests/integration.mjs. При развёртывании проверьте postMessage на реальном HTTPS origin, CORS, CSP и обновления игрового iframe.
