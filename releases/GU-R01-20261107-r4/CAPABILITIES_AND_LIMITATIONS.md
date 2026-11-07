# Capabilities and limitations

Shipped and reachable in the UI:

- Guided setup for Orbit Supply and for a supplied URL with a visible milestone.
- One model-chosen browser path. The model may return only a candidate id from the controls on the page.
- Independent replay from a new fixture reset. A pass requires the registered cart check, not a success-looking screen.
- Fixture regression checks for the ordinary, shortcut, and Express routes. They are labeled fixture checks.
- Run library, evidence screenshots, and read-only playback.
- Stop. A stop during setup ends as `stopped_by_user`.

The accepted live run is `run_c6252c9a4a6e4ba2`, status `passed`, stop `completed_target`, build `orbit-buggy-v1`.

Not in this release: adaptive search, prefix exclusion, recommendation review, retest after a fix, competitor comparison, a custom model endpoint, keyboard-only checks, and multiple runtime workers.

Provider: OpenRouter `anthropic/claude-sonnet-4.6` for browser planning, text only. Screenshots are stored and are not sent to the model. No dollar cap is configured; reported spend is shown and unknown spend stays unknown. Playback does not need the key.

Restoration is the Orbit reset adapter for the demo shop, and a fresh browser context for a supplied page. A supplied page without a server reset is not a strict comparable replay when restoration is unknown.
