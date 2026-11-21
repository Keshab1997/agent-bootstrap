# সাধারণ ফ্লো — repo attach, Captain বলে দেয়, worker push করে, Captain CI চালায়

**খুব সহজ নিয়ম:** প্রতিটা worker chat-এ Arena UI থেকে target repo attach করে
দিন। Captain এক message-এ বলে দেবে কী করতে হবে; worker শুধু `allowed` file
edit করে নিজের `arena/*` branch push করবে; Captain GitHub থেকে এসে diff দেখে,
**CI চালাবে**, লাল হলে নিজেই ঠিক করবে, তারপর `main`-এ land করবে।

## ১. Captain-কে repo আর কাজ বলুন

Captain চালু থাকলে starter আবার লাগবে না। নতুন হলে
[`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) দিন (অথবা
`captain_up.sh`)। সেভ করা login কাজ করলে Captain নতুন approval চাইবে না;
code দেখালেই শুধু GitHub-এ approve করুন।

```text
<repo>-তে <কাজগুলো> ভাগ করে A/B/C-কে বড় বড় task দাও।
প্রতি worker-এর জন্য এক-একটা assignment message দাও; review, CI আর main তুমি সামলাও।
```

**গতি সবার আগে:** Captain প্রতিটি worker-কে বড়, সম্পূর্ণ কাজ দেবে (পুরো
feature/screen + test — ছোট ছোট টুকরো নয়), সব worker-এর message একসাথে দেবে।
Worker-রা কাজ করার ফাঁকেই Captain নিজের অংশ (shared file, review, CI, ছোট
fix) নিজেই শেষ করবে — বসে অপেক্ষা করবে না।

## ২. Worker chat শুরু করা (repo attach করে)

1. নতুন chat খুলে **target repo attach** করুন।
2. Captain যে **এক message** দেবে সেটাই paste করুন — brief-এর path, allowed
   file, একটাই check আর `git commit` → `git push origin HEAD` → `PUSHED` রিপোর্ট।
3. Worker নিজের `arena/*` branch-এ কাজ push করে জানিয়ে দেবে। আপনি শুধু
   `AGENT A PUSHED …` ব্লকটা Captain-কে দেবেন (বা Captain নিজেই GitHub থেকে
   দেখে নেবে)।

একটাই পদ্ধতি — আলাদা tool বা pairing-এর দরকার নেই। Worker কিছু চাইলে শুধু
`AGENT A BLOCKED` + কারণ জানাবে।

## ৩. Push যাচাই, CI, আর পরের task

Worker `PUSHED` দিলে Captain ওই exact `base..tip` দেখে নেয় (কোনো `allowed`
file-এর বাইরে গেছে কি না, secret নেই কি না), তারপর ওই branch-এ CI চালায়:

```text
A-এর PUSHED branch দেখে CI চালাও; লাল হলে log পড়ে ঠিক করো,
সবুজ হলে main-এ land করো, আর A-কে তার পরের বড় কাজের message দাও।
```

Approved tracker issue থাকলে worker (বা Captain) একটা `@Keshab1997` comment
করতে পারে — বাধ্যতামূলক নয়; chat-এর `PUSHED` ব্লকই যথেষ্ট। Checkpoint যাচাই
হলেই Captain সঙ্গে সঙ্গে পরের বড় assignment পাঠাবে।

## ৪. Batch সত্যিই শেষ হলে

```text
Finalize batch <id> — কী land হয়েছে এবং কী বাকি দেখাও।
```

Batch শেষে Captain প্রতিটা verified `arena/*` branch review করে, CI সবুজ দেখে
`main`-এ land করবে — CI চালানো ও লাল ঠিক করা Captain-এর কাজ, আপনার কিছু করতে
হবে না।

আরও: [Worker Starter](WORKER_START_PROMPT.md) · [GitHub brief-এর নিয়ম](GITHUB_BRIEFS.md) · [Fast Lane commands](FASTLANE.md) · [Captain login](../NEXT_TIME_BANGLA.md)
