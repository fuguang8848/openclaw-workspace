# Workspace Plugins

Custom OpenClaw plugins owned by 浮光 / V.

## v-pre-send-guard

OpenClaw plugin that blocks outbound messages containing V's internal
codeword placeholder. Forces V to rewrite without the placeholder.

Layer 3 of the SOP #43 three-layer defense.

| | |
|---|---|
| Repo | https://github.com/fuguang8848/openclaw-v-pre-send-guard |
| Status | installed, gateway loaded (priority 100) |
| Listens to | `message_sending` hook |
| Action on hit | `{ cancel: true, cancelReason: ... }` |
| Pairs with | `tools/v-pre-send-filter.py` (Layer 1), `SOUL.md` (Layer 2) |
