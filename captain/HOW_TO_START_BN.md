# একই worker chat-এ পরপর কাজ — Captain Fast Lane

**কাজ শেষ = branch checkpoint, PR merge নয়।** Arena-তে repo-linked chat-এ একটাই PR; সেই PR **merge বা close** হলে ওই chat আর GitHub-এ push করতে পারে না। Fast Lane এই সীমা বদলায় না—একই chat-এ একাধিক কাজের checkpoint নেওয়া যায়, তারপর batch শেষ হলে PR নিয়ে সিদ্ধান্ত হয়। [Arena-র নির্দেশনা](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)

## ১. Captain-কে কী বলবেন

Captain চালু থাকলে আবার starter দিতে হবে না। নতুন হলে [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) দিন। নিজের saved login কাজ করলে Captain approval চাইবে না। সত্যিই code দেখালে শুধু GitHub-এর [device page](https://github.com/login/device)-এ approve করুন। Turn শেষ হলে একই code `device_pair.py poll 60` দিয়ে resume হয়।

```text
<repo>-তে <কাজগুলো> ভাগ করে A/B/C-র Fast Lane briefs দাও।
একই worker chats রাখব; এখন কোনো worker PR merge/close নয়।
```

Captain goal, files, interface ও check আলাদা করে ছোট brief দেবে। এক worker-কে একসঙ্গে একটি কাজ, দুই worker-কে একই file নয়।

## ২. কোন worker chat ব্যবহার করবেন

| পরিস্থিতি | কী করবেন |
|---|---|
| চালু repo-linked chat | একই `arena/*` branch রাখুন। Checkpoint push হলে PR খুলবেন না; আগেই খোলা থাকলে সেটি merge বা close করবেন না। |
| ঘন ঘন নতুন `main` থেকে কাজ দরকার | **Repo attach না করে** সাধারণ Agent Mode chat রাখুন। Worker নিজের অনুমোদিত access-এ task-পিছু নতুন `agent/A/<task>` branch বানায়। আলাদা GitHub PR/merge worker chat-এর অংশ নয়। |
| Linked PR আগেই merge/close, বা chat অচল | পুরোনো chat-এ নতুন কাজ নয়। Captain-এর ছোট handoff দিয়ে fresh chat। |

পুরোনো কাজ মাঝপথে থাকলে সেটার branch, base ও check বদলাবেন না। নতুন runner শুরু করার জন্য ওই edits reset করার দরকার নেই।

## ৩. প্রতি কাজের পর Captain-কে রিপোর্ট দিন

Worker `AGENT A PUSHED` বললে পুরো ছোট block দিন: repo, task, branch, `base_sha`, pushed `sha`, files, check। **কোনো app ফাইল download/upload করতে হবে না।** `BLOCKED` হলে আসল সমস্যা দিন; সেটা push নয়। Captain GitHub থেকে ওই range যাচাই করে review করবে।

```text
A-এর checkpoint যাচাই করো। ঠিক থাকলে একই A chat-এ দেওয়ার পরের brief দাও।
```

Captain পরের brief-এ আগের verified SHA বসাবে। Worker-এর branch-এ দরকারি upstream change না থাকলে Captain নতুন base থেকে কাজ দেবে; পুরোনো branch reset করবে না। Flutter test দরকার হলে brief-এ সঠিক version pin ও test file থাকবে; lockfile বদলে test পাশ করা চলবে না।

## ৪. Batch সত্যিই শেষ হলে

```text
Finalize batch <id> — কী land হয়েছে, কী বাকি, আর PR দরকার কি না দেখাও।
```

Captain আগে সব checkpoint ও diff দেখবে। PR লাগলে clean Captain review branch অগ্রাধিকার পাবে। Linked worker PR merge/close করলে সেটি **শেষ ধাপ**—বাকি local কাজ safe না হওয়া পর্যন্ত নয়। নতুন chat দরকার হলে Captain আগের checkpoint ও পরের goal মিলে ছোট handoff দেবে। Manual CI এখনও আপনার সিদ্ধান্ত।

**Credentials:** নতুন standalone workspace-এ নিজের প্রথম approval লাগতে পারে। Saved refresh থাকলে expiry-তে আবার browser খুলতে হয় না। Token, refresh token বা 2FA code কখনো chat/brief-এ দেবেন না। এক worker-এর token আরেক worker-কে দেবেন না।

আরও: [Fast Lane commands](FASTLANE.md) · [নতুন session-এ login](../NEXT_TIME_BANGLA.md)
