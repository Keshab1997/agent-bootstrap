# GitHub-এ brief, Device Flow-তে কাজ — Captain Fast Lane

**এখন আর Arena-তে প্রতিটা worker chat-এ repo attach করতে হবে না।** Captain ও
Worker — সবাই **GitHub Device Flow** (`gh_app.py`) দিয়ে সংযুক্ত হবে। একবার
approve করলে ওই একই Worker chat একাধিক task এবং এমনকি একাধিক repo-তেও কাজ
করতে পারবে (Arena-র ১-PR সীমা বা branch-lock ঝামেলা নেই)।

## ১. Captain-কে repo আর কাজ বলুন

Captain চালু থাকলে starter আবার লাগবে না। নতুন হলে
[`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) দিন (অথবা
`captain_up.sh`)। সেভ করা login কাজ করলে Captain নতুন approval চাইবে না;
code দেখালেই শুধু GitHub-এ approve করুন।

```text
<repo>-তে <কাজগুলো> ভাগ করে A/B/C-র brief GitHub-এ push করো।
প্রতি worker-এর জন্য pinned link দাও।
```

**গতি সবার আগে:** Captain প্রতিটি worker-কে বড়, সম্পূর্ণ কাজ দেবে (পুরো
feature/screen + test — ছোট ছোট টুকরো নয়), সব worker-এর link একসাথে দেবে।
Worker-রা কাজ করার ফাঁকে Captain নিজের অংশ (shared file, জোড়া লাগানো, ছোট
fix) নিজেই শেষ করবে — বসে অপেক্ষা করবে না।

## ২. Worker chat শুরু করা (কোনো repo attach ছাড়াই)

1. সাধারণ নতুন chat খুলুন (Arena UI-তে repo attach করার দরকার নেই)।
2. প্রথমবার chat-এ [`WORKER_START_PROMPT.md`](WORKER_START_PROMPT.md) (বা
   `worker_up.sh`) আর Captain-এর দেওয়া এক লাইনের link দিন।
3. Worker `XXXX-XXXX` device code দেখালে শুধু একবার
   https://github.com/login/device -এ গিয়ে approve করুন। একবার paired হলে ওই
   একই Worker chat-এ পরপর অনেকগুলো task ও যেকোনো repo-তে কাজ চালানো যাবে।
4. Worker নিজেই `worker_lane.py fetch-brief` দিয়ে GitHub থেকে brief নামাবে,
   `agent/<W>/<task>` branch-এ কোড ও test চালিয়ে push করবে।

## ৩. Push যাচাই হলে mention ও পরের task

Worker test চালিয়ে checkpoint push করবে এবং `worker_lane.py mention` দিয়ে
brief-এ দেওয়া issue-তে `@Keshab1997` comment পোস্ট করবে (task, branch, base
SHA, pushed SHA, files, check ও commit link সহ)। Tracker issue না থাকলে
chat-এই `PUSHED` রিপোর্ট দেবে।

```text
Batch <id>-এর GitHub রিপোর্ট দেখে A-এর checkpoint যাচাই করো।
ঠিক থাকলে A-এর পরের pinned brief publish করো।
```

Checkpoint যাচাই হলেই Captain সঙ্গে সঙ্গে পরের বড় brief দেবে; পুরো review
আর integration Captain-এর দিকে চলবে। পরের task `main` থেকে বা দরকার হলে
আগের verified commit (`base_sha` + `base_branch`) থেকে chain করা যাবে।

*(Optional: আগে থেকে কোনো chat-এ Arena repo attach করা থাকলে সেটাও `"arena"`
brief দিয়ে চালানো যাবে, তবে নতুন কাজের জন্য Device Flow-ই primary।)*

## ৪. Batch সত্যিই শেষ হলে

```text
Finalize batch <id> — কী land হয়েছে এবং কী বাকি দেখাও।
```

Batch শেষে Captain সব verified `agent/*` commit review করে `main`-এ land
করবে; CI dispatch আপনার সিদ্ধান্ত (বা আপনার অনুমতিতে `ci_dispatch.py`)।

আরও: [Worker Starter](WORKER_START_PROMPT.md) · [GitHub brief-এর নিয়ম](GITHUB_BRIEFS.md) · [Fast Lane commands](FASTLANE.md) · [Captain login](../NEXT_TIME_BANGLA.md)
