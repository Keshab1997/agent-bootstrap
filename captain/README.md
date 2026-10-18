# captain/ — এক Captain, workers-এর সরাসরি branch push

**কোনো ফাইল download/upload করে handoff করতে হবে না।** Workers নিজেদের
GitHub branch-এ push করবে; Captain সেখান থেকে fetch করে review/merge করবে।

```text
Keshab → Captain → brief A/B/C → workers → GitHub worker branches
            ↑                               ↓
            └──────── git fetch / review ──┘
            ↓
       check → merge → main push → report
```

## শুরু

1. Captain chat-এ root-এর `CAPTAIN_START_PROMPT.md` দিন। সে saved session
   restore করবে; সত্যিই দরকার হলে approval চাইবে।
2. Repo ও কাজ বলুন। Captain ফাইল ভাগ করে A/B/C brief লিখবে।
3. Brief-গুলো worker chat-এ দিন। **সম্ভব হলে একই worker chats/workspaces রাখুন।**
   নতুন workspace-এর প্রথমবার approval লাগতে পারে; পরে saved login/refresh reuse হবে।
4. Worker নিজের `agent/A|B|C/...` branch push করবে। Captain-কে শুধু জানান কারা
   push করেছে; সে `git fetch` করে নিজেই পরিবর্তন নিতে পারবে।
5. Captain diff review → cheap check → merge → `main` push → পাঁচ লাইনের report।

## ফাইল

| ফাইল | কাজ |
|---|---|
| `CAPTAIN_PROMPT.md` | Captain-এর নিয়ম, file split, review/merge, report |
| `WORKER_BRIEF_TEMPLATE.md` | Worker-এর task, allowed files, check ও branch-push brief |
| `examples/WORKER_A_example.md`, `WORKER_B_example.md`, `WORKER_C_example.md` | ভরা branch-push উদাহরণ |
| `HOW_TO_START_BN.md` | মানুষের জন্য ধাপে ধাপে নির্দেশনা |

প্রত্যেক workspace নিজের credentials রাখবে। Token/refresh token কখনো share হবে
না। Fresh workspace, revoked credentials বা হারানো refresh হলে আবার approval
লাগতে পারে—কখনোই “আর কোনোদিন লাগবে না” ধরে নেবেন না। Authenticator-এর 2FA code
এই app authorization-এর বিকল্প নয়।

Captain tags/releases, secrets/settings/workflows বদলাবে না অনুমতি ছাড়া।
কোনো branch diff না পড়ে merge করবে না। কোনো worker CI dispatch করবে না।
