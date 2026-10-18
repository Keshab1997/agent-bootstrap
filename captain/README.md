# captain/ — এক Captain, কম authorization

**Captain-ই GitHub login ও publish করবে। Public repo-র workers default-এ login
ছাড়া কাজ করে `.patch` দেবে।** একই Captain workspace-এর token/refresh রাখা থাকলে
প্রতি worker-এর জন্য আলাদা approval লাগে না।

```text
Keshab → Captain → frozen brief A/B/C → workers (local branches, no push)
            ↑                              ↓
            └──── patch + report attachment ┘
            ↓
       review → check → commit → main push → report
```

## শুরু

1. Captain chat-এ root-এর `CAPTAIN_START_PROMPT.md` দিন। সে saved session
   restore করবে; সত্যিই দরকার হলে তবেই approval চাইবে।
2. Repo ও কাজ বলুন। Captain ফাইল ভাগ করে **patch briefs** লিখবে।
3. Brief-গুলো আলাদা worker chat-এ দিন। Public repo-তে authorization লাগবে না।
4. Workers-এর **আসল `.patch` ফাইল report-সহ Captain চ্যাটে attach করুন**। শুধু
   অন্য চ্যাটের local path দিলে Captain পড়তে পারবে না।
5. Captain diff review → cheap check → `main` push → পাঁচ লাইনের report।

## কোন mode কখন

| Mode | ব্যবহার | Worker approval |
|---|---|---|
| **Patch — default** | Public repo, file attachment দিয়ে handoff সম্ভব | নেই; worker push করবে না |
| Branch — explicit opt-in | Private repo বা patch handoff অসুবিধাজনক | নিজস্ব pairing লাগতে পারে; Captain আগে জানাবে |

Private source-কে public করা বা Captain-এর `secrets/` worker-কে দেওয়া যাবে না।
Patch handoff কম browser approval-এর বিনিময়ে file attachment-এর এক ধাপ যোগ করে।
একদম নতুন Captain workspace-এ প্রথম approval এখনও লাগতে পারে।

## ফাইল

| ফাইল | কাজ |
|---|---|
| `CAPTAIN_PROMPT.md` | Captain-এর নিয়ম, file split, দুই mode-এর review/merge, report |
| `WORKER_PATCH_BRIEF_TEMPLATE.md` | **Default public-repo brief**, no login/no push |
| `examples/WORKER_PATCH_example.md` | সম্পূর্ণ ভরা patch-mode উদাহরণ |
| `WORKER_BRIEF_TEMPLATE.md` | Explicit authenticated branch/push alternative |
| `examples/WORKER_A_example.md`, `WORKER_B_example.md`, `WORKER_C_example.md` | Branch-mode উদাহরণ; default নয় |
| `HOW_TO_START_BN.md` | মানুষের জন্য ধাপে ধাপে নির্দেশনা |

Captain tags/releases, secrets/settings/workflows বদলাবে না অনুমতি ছাড়া।
কোনো patch/branch diff না পড়ে merge করবে না। কোনো worker CI dispatch করবে না।
