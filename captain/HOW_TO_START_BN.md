# 🚀 Captain শুরু করুন — file handoff নয়, সরাসরি branch push

> **এক লাইন:** Captain prompt → কাজ বলুন → workers-কে brief → তারা branch push
> করবে → Captain নিজেই fetch/review/merge করবে।

সম্ভব হলে একই Captain এবং A/B/C worker chats/workspaces ব্যবহার চালিয়ে যান।
প্রতিটির saved login/refresh সেখানেই থাকবে। আলাদা নতুন workspace-এ প্রথম
approval লাগতে পারে; শুধু chat-এর নাম এক রাখলে credentials স্থানান্তর হয় না।

## ১. Captain চ্যাট

Root-এর [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) দিন। সে repo
clone করে playbook পড়বে এবং saved GitHub session restore করবে।

- `ALREADY CONNECTED` বললে কিছুই করতে হবে না।
- Access token expire হলে আগে saved refresh চেষ্টা করবে।
- সত্যিই code দেখালেই https://github.com/login/device-এ approve করুন।
- Turn শেষ হলে নতুন code নয়: `python3 device_pair.py poll 60` দিয়ে একইটি resume।
- Network error হলে retry; নতুন approval ওই সমস্যা ঠিক করবে না।

শেষে সে বলবে: **Captain ready — কাজ বলো।** এই চ্যাটে ইতিমধ্যে setup থাকলে
সোজা কাজের কথাই বলুন, আবার starter paste করার দরকার নেই।

## ২. কাজ বলুন

উদাহরণ:

```text
Batch 1 বানাও:
1) docify — home screen 360px ফোনে overflow ঠিক করতে হবে
2) quizbaaz — results screen-এ tap feedback চাই
3) flutter-builder — README-র বাংলা অংশে বানান ঠিক করতে হবে

A/B/C-র branch-push briefs দাও; আগের worker chats-গুলোতেই কাজ দেব।
```

Captain goal, allowed files, exact interface, cheap check এবং আলাদা branch
name ভরে দেবে। এক ফাইল দুই worker পাবে না। ছোট কাজ হলে Captain নিজেই করতে পারে।

## ৩. Worker চ্যাটগুলো

A/B/C brief-গুলো সংশ্লিষ্ট worker chat-এ দিন। Worker নিজের saved login restore
করবে। একেবারে নতুন worker হলে প্রথমবার code approve করতে হতে পারে।

কাজ ও check শেষে worker নিজের `agent/A|B|C/...` branch push করবে—`main` নয়।
Existing branch বা অসমাপ্ত কাজ overwrite/reset করবে না। শেষে report দেবে:

```text
AGENT A DONE
branch: agent/A/home-overflow
sha: <আসল commit SHA>
files: <আসল পরিবর্তিত ফাইল>
check: <নির্ধারিত check এবং আসল ফল>
changed: <পরিবর্তনের সারাংশ>
not touched: <বাদ রাখা অংশ>
blocked: <none বা আসল সমস্যা>
```

## ৪. Captain-কে শুধু জানান

```text
A/B/C push করেছে — fetch করে diff দেখে merge করো।
```

চাইলে workers-এর report-ও paste করতে পারেন; **কোনো ফাইল download বা attach
করতে হবে না**। Captain পরিচিত branch names ধরে GitHub থেকে কাজগুলো আনবে।
Push না হলে শুধু worker-এর local workspace থেকে Captain কাজ পাবে না; worker-কে
নিজের branch push শেষ করতে হবে।

## ৫. Review ও publish

Captain actual diff পড়বে, scope/secrets যাচাই করবে, review branch-এ নির্ধারিত
check চালাবে, তারপর `main`-এ integrate/push করে পাঁচ লাইনের report দেবে।
কোনো tag/release/secret/settings/workflow বদলানোর আগে অনুমতি নেবে।

## Authorization সম্পর্কে পরিষ্কার কথা

- একই workspace-এ valid saved refresh থাকলে সাধারণ access-token expiry-তে
  browser খুলতে হবে না। একেবারে নতুন workspace বা revoked/lost credentials
  হলে আবার approval লাগতে পারে।
- Authenticator app-এর ৬-digit GitHub code হলো account login-এর **2FA**;
  agent-এর `XXXX-XXXX` device code হলো app-access request। একটির বদলে অন্যটি
  চলে না। GitHub-এর নিজের login পেজে চাইলে শুধু সেখানেই 2FA code দিন।
- Token, refresh token, authenticator seed বা recovery codes chat/brief-এ দেবেন
  না। এক agent-এর credentials আরেকজনকে কপি করবেন না।

দরকারি গাইড: [`NEXT_TIME_BANGLA.md`](../NEXT_TIME_BANGLA.md)। নতুন server,
PAT/private key বা repository setting লাগবে না এই branch-push workflow-এর জন্য।
