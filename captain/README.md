# captain/ — multi-agent playbook (one captain, several workers)

Keshab-এর setup: **একজন agent = Captain** (তোমার সাথে শুধু সে-ই কথা বলে), আর তার হাতে লেখা
brief নিয়ে **worker A/B/C** — নিজের sandbox, নিজের branch, `main` কখনো ছোঁয় না।

```
Keshab ──► CAPTAIN ──brief A/B/C──► workers (agent/A|B|C/<slug> branches)
              │                              │
              └──◄──── review → fix → merge → main ──► report ──► Keshab
```

## শুরু করো এভাবে

1. নতুন agent chat-এ **`CAPTAIN_START_PROMPT.md`** (repo root-এ) পুরোটা paste করো।
   Captain নিজে pair হবে, clone করবে, আর এই ফোল্ডারের playbook পড়ে নেবে।
2. তাকে বলো কী কাজ চাও (কোন repo, কী সমস্যা)।
3. সে **`WORKER_BRIEF_TEMPLATE.md`** ভরে A/B/C brief লিখে দেবে — প্রতিটা **আলাদা**
   worker chat-এ paste করো।
4. Worker-রা `AGENT X DONE` ব্লক ফেরত দেবে → Captain-কে paste করো (বা সে নিজেই
   `git fetch` করে দেখে নেবে)।
5. Captain check → fix → merge → `main` push → ৫ লাইনের report।

## এই ফোল্ডারের ফাইল

| ফাইল | কী |
|---|---|
| `CAPTAIN_PROMPT.md` | Captain-এর পুরো playbook — hard rules, batch loop, review checklist, merge discipline, report format |
| `WORKER_BRIEF_TEMPLATE.md` | brief template — Captain এটা ভরে worker-কে দেয় |
| `examples/WORKER_A_example.md` | ভরা উদাহরণ — Dart edit + একটা test file (`docify`) |
| `examples/WORKER_B_example.md` | ভরা উদাহরণ — একই repo, অন্য ফাইল, একই batch |
| `examples/WORKER_C_example.md` | ভরা উদাহরণ — আলাদা repo (`flutter-builder`) → conflict অসম্ভব |
| `HOW_TO_START_BN.md` | বাংলায় ধাপে ধাপে — কী লিখবে, কোন ক্রমে |

## যা কখনো Captain próprio করবে না

`v*` tag / release · repository secrets / settings · history rewrite · **`main`-এর বাইরে
কিছু merge না পড়ে** · worker-দের জন্য ভারী check (শুধু `preflight.py` বা `pytest -q`)।

## নোট

- প্রতিটা worker আলাদা sandbox → আলাদা pairing (এক approve করে)। `secrets/` কখনো
  এক agent থেকে আরেকজনকে কপি করো না — refresh token single-use।
- এই ফোল্ডারের ফাইলগুলো `agent-bootstrap`-এর সাথে sync থাকে; উৎস কপি (copy-পেজ সহ)
  Keshab-এর workspace-এ `agent-captain-kit/`-তেও আছে।
