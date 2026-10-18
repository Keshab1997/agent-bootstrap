# 🚀 Captain শুরু করুন — workers-এর জন্য browser approval নয়

> **এক লাইন:** Captain prompt → কাজ বলুন → workers-কে brief → তাদের patch
> ফাইল Captain-কে attach → Captain review করে publish করবে।

Public repo-র default workflow-তে শুধু Captain-এর GitHub access লাগে। একই
Captain workspace ব্যবহার চালিয়ে গেলে saved token/refresh reuse হয়। একদম
নতুন workspace-এ প্রথম approval এখনও দরকার হতে পারে।

## ১. Captain চ্যাট

Root-এর [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) পুরোটা নতুন
agent chat-এ paste করুন। সে repo clone করে playbook নিজে পড়বে।

- `ALREADY CONNECTED` বললে কিছুই করতে হবে না।
- Access token expire হলে আগে saved refresh চেষ্টা করবে।
- সত্যিই code দেখালেই https://github.com/login/device-এ approve করুন।
- Turn শেষ হলে নতুন code নয়: `python3 device_pair.py poll 60` দিয়ে একইটি resume।
- Network error হলে retry; approval বাড়িয়ে ওই সমস্যা ঠিক হয় না।

শেষে সে বলবে: **Captain ready — কাজ বলো।**

## ২. কাজ বলুন

উদাহরণ:

```text
Batch 1 বানাও:
1) docify — home screen 360px ফোনে overflow ঠিক করতে হবে
2) quizbaaz — results screen-এ tap feedback চাই
3) flutter-builder — README-র বাংলা অংশে একটা বানান ভুল আছে

Repo-গুলো public কিনা যাচাই করে no-login patch briefs দাও। Private হলে আগে জানাও।
```

Captain প্রতিটি brief-এ নির্দিষ্ট base commit, goal, allowed files, exact
interface, check ও patch filename ভরে দেবে। এক ফাইল দুই worker পাবে না।

## ৩. Worker চ্যাট

A/B/C brief-গুলো আলাদা নতুন chat-এ দিন। **Patch brief-এ worker authorize চাইবে
না এবং push করবে না।** সে public source clone করে local branch-এ কাজ করবে,
নির্ধারিত check চালাবে, শেষে একটি `.patch` ফাইল ও report দেবে।

Report-এর ধরন:

```text
AGENT A DONE
mode: patch (no GitHub authorization)
repo: Keshab1997/docify
base: <brief-এ থাকা পূর্ণ SHA>
branch: agent/A/home-overflow (local only)
sha: <worker-এর local commit SHA>
patch: A-home-overflow.patch
sha256: <ফাইলের আসল checksum>
files: lib/screens/home_screen.dart, test/home_screen_test.dart
check: flutter test test/home_screen_test.dart → <আসল ফল>
changed: <আসল পরিবর্তন>
not touched: theme, pubspec, workflows
blocked: none
```

এটি শুধু report-এর উদাহরণ, কোনো test pass হওয়ার দাবি নয়। Worker আসল ফল লিখবে।

## ৪. Captain-কে patch দিন

Worker-এর `.patch` ফাইল download করে **Captain চ্যাটে attach করুন**, report-টিও
paste করুন। A/B/C যতজন শেষ করেছে তাদেরগুলো একসঙ্গে দেওয়া যায়।

**শুধু `/home/user/handoff/...` path paste করলে হবে না**—আলাদা sandbox-এর file
Captain দেখতে পায় না। Patch mode-এ remote branch-ও নেই; `git fetch` দিয়ে ওই
কাজ পাওয়া যাবে না। এই একবার file handoff-ই worker authorization-এর বিকল্প।

## ৫. Review, check, publish

Captain checksum/base/path/scope/secrets যাচাই করে **আসল diff পড়বে**। তারপর
আলাদা review branch-এ patch apply, নির্ধারিত check, commit এবং `main`-এ publish।
Conflict হলে আন্দাজে বা force দিয়ে apply করবে না।

তার report:

```text
Batch 1: A merged (<sha7>), B merged (<sha7>), C pending — <কারণ>
Changed: <প্রতি workstream-এর সংক্ষিপ্ত পরিবর্তন>
Evidence: <আসল test/check ফল>
Not touched: <secrets/settings/workflows ইত্যাদি>
Next: <পরের কাজ বা সিদ্ধান্ত>
```

Tag/release/secret/settings/workflow বদলাতে হলে আগে আপনার অনুমতি লাগবে।

## Private repo বা attachment নিয়ে সমস্যা হলে

Captain আগে জানিয়ে **branch mode** নিতে পারে। তখন worker-এর নিজের pairing
লাগবে, সে `agent/A|B|C/...` branch push করবে, Captain `git fetch` করে review করবে।
পুরোনো `WORKER_BRIEF_TEMPLATE.md` এবং A/B/C branch examples এই mode-এর জন্য রাখা আছে।

কখনো Captain-এর token/refresh token worker-কে কপি করবেন না, source-কে public
করবেন না, public repo-তে credential রেখে approval বাদ দেওয়ার চেষ্টা করবেন না।

## কোন ফাইল কোথায়

- প্রথম paste: `CAPTAIN_START_PROMPT.md`
- Captain-এর playbook: `captain/CAPTAIN_PROMPT.md`
- Default brief: `captain/WORKER_PATCH_BRIEF_TEMPLATE.md`
- ভরা patch example: `captain/examples/WORKER_PATCH_example.md`
- Auth troubleshooting: `NEXT_TIME_BANGLA.md`

নতুন server, PAT, private key বা repository setting লাগবে না। শুধু বর্তমান
bootstrap code ও playbook ব্যবহার করলেই এই workflow পাওয়া যাবে।
