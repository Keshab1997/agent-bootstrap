# GitHub-এ brief, Arena-তে কাজ — Captain Fast Lane

## ১. Captain-কে repo আর কাজ বলুন

Captain চালু থাকলে starter আবার লাগবে না। নতুন হলে
[`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) দিন। সেভ করা login কাজ
করলে Captain approval চাইবে না; code দেখালেই শুধু GitHub-এ approve করুন।

```text
<repo>-তে <কাজগুলো> ভাগ করে A/B/C-র brief GitHub-এ push করো।
প্রতি worker-এর জন্য pinned link দাও। এখন কোনো worker PR merge/close নয়।
```

**গতি সবার আগে:** Captain প্রতিটি worker-কে বড়, সম্পূর্ণ কাজ দেবে (পুরো
feature/screen + test — ছোট ছোট টুকরো নয়), সব worker-এর link একসাথে দেবে।
Worker-রা কাজ করার ফাঁকে Captain নিজের অংশ (shared file, জোড়া লাগানো, ছোট
fix) নিজেই শেষ করবে — বসে অপেক্ষা করবে না।

Captain একই কাজের repo-তে `captain/briefs/<batch>` branch-এ `BRIEF.md` আর
`task.json` push করবে। `main`-এ brief যাবে না। GitHub-এ commit যাচাই করার
পর Captain প্রতি worker-এর জন্য এক লাইনের link দেবে। পুরো brief copy/paste
বা কোনো ফাইল download/upload করতে হবে না।

## ২. Worker chat খোলার সময় কাজের repo attach করুন

1. Arena Agent Mode-এ GitHub on করুন। দরকার হলে **Manage repositories**-এ
   কাজের repo-র access দিন। Worker chat শুরু করার সময় **ওই repo-টাই**
   select করুন; অন্য project-এর জন্য `agent-bootstrap` attach করবেন না।
2. ভুল repo বা repo attach না থাকলে worker কাজ শুরু করবে না। সঠিক repo
   attach করে নতুন chat খুলুন; clone করে বা নতুন token দিয়ে চালাবেন না।
3. Captain-এর এক লাইনের pinned link দিন। Worker একই GitHub commit থেকে
   brief আর JSON পড়ে নিজের আসল `arena/*` branch-এ শুধু বরাদ্দ করা file-এ
   কাজ করবে। চালু সঠিক repo-linked chat হলে সেটা reuse করুন।

[Arena-র repo connect নির্দেশনা](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode)

## ৩. Push যাচাই হলে mention

Worker check চালিয়ে checkpoint push করবে। GitHub-এর branch tip মিলে গেলে
brief-এ দেওয়া অনুমোদিত issue-তে `@Keshab1997` mention করবে: task, branch,
base SHA, pushed SHA, files, check ও commit link সহ। Comment access না থাকলে
Arena-তে `PUSHED` আর `MENTION PENDING` দেখাবে; দরকার হলে Captain যাচাই করে
নিজের অনুমোদিত access দিয়ে mention দেবে। Push না হলে `BLOCKED`, done নয়।

```text
Batch <id>-এর GitHub রিপোর্ট দেখে A-এর checkpoint যাচাই করো।
ঠিক থাকলে একই A chat-এর পরের pinned brief publish করো।
```

Checkpoint যাচাই হলেই Captain সঙ্গে সঙ্গে পরের বড় brief দেবে; পুরো review
আর integration worker কাজ করার সময়েই চলবে। Captain শুধু ওই task-এর
base→tip diff review করবে। পরের brief-এ একই branch আর শেষ যাচাই করা SHA
যাবে। ওই base-এ দরকারি upstream code না থাকলে নতুন repo-linked chat নিন;
পুরোনো branch reset/rebase করবেন না।

## ৪. Batch সত্যিই শেষ হলে

```text
Finalize batch <id> — কী land হয়েছে এবং কী বাকি দেখাও।
```

**প্রতি task-এ PR merge/close নয়।** Arena-তে [এক linked chat-এ এক PR](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode)।
ওই PR [merge বা close হলে একই chat আর push করতে পারে না](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)।
Batch শেষে Captain review করবে; CI dispatch আপনার সিদ্ধান্ত। আগে থেকে
চলতে থাকা কাজ থাকলে তার original branch, base ও check বদলাবেন না।

আরও: [GitHub brief-এর নিয়ম](GITHUB_BRIEFS.md) · [Fast Lane commands](FASTLANE.md) · [Captain login](../NEXT_TIME_BANGLA.md)
