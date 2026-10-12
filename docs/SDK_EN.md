# Aurevix SDK v1
Copy aurevix.js into the game ZIP. For ESM also copy aurevix.mjs; declarations are aurevix.d.ts. No CDN or credentials inside game code.

```html
<script src="aurevix.js"></script>
<script>
(async () => {
  const sdk = new AurevixSDK('YOUR_GAME_ID');
  try {
    const state = await sdk.init();
    if (state.authenticated) await sdk.submitScore(120);
    const board = await sdk.getLeaderboard();
    console.log(board.items); // competitive=false
  } catch (error) { console.warn(error.code); }
})();
</script>
```

The player appends platformOrigin to the iframe URL. You may explicitly pass `{parentOrigin:'https://your-project.vercel.app'}`. SDK requests target that exact origin and only accept messages from the parent window at that origin. Parent checks iframe source, opaque null origin, channel, request id and game identity. Credentials remain in the parent; play_token never enters the game. All methods return promises: init,submitScore,getLeaderboard; destroy removes listeners and rejects pending requests. Request timeout 10s, maximum 10 pending requests; integer score range 0..1_000_000. One score per play session; Restart for another run.

Errors: invalid_parent_origin,not_embedded,invalid_score,timeout,too_many_requests,unauthorized,invalid_play_session,destroyed,request_failed. Handle errors and guest play. TypeScript module example: `import {AurevixSDK} from './aurevix.mjs'`; map the provided declaration to the module in your bundler if needed.

**Anti-cheat boundary:** server validates account/game binding, types/bounds and replay, not arbitrary client game rules. Results are verified=false and competitive=false. A real competitive game needs its own authoritative rules, seed, action replay and timing verifier. Do not award prizes based on these records.

Tests: frontend/tests/sdk.test.mjs, backend/tests/test_backend.py and the live frontend-client integration test. Recheck postMessage/CSP/CORS on the real deployed HTTPS origins.
