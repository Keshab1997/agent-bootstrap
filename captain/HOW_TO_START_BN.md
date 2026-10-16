# 🚀 প্রথম থেকে শুরু — কী লিখবে, কোন ক্রমে

> **মনে রাখার এক লাইন:** *"Captain prompt" — তারপর "কী কাজ" — তারপর ও যেই brief দেবে সেগুলো আলাদা চ্যাটে paste।*

মোট **৪টা চ্যাট** লাগবে: ১টা Captain + ৩টা worker। প্রতিটা চ্যাট প্রথমবার একটা করে code
দেখাবে (মোট ৩-৪ বার ব্রাউজারে Approve), তারপর কেউ আর কিছু চাইবে না।

---

## ধাপ ১ — Captain-এর চ্যাট (নতুন agent session)

নতুন chat খুলে শুধু এটুকু paste করো — **`CAPTAIN_START_PROMPT.md`-এর পুরোটা**:

```text
# You are the CAPTAIN. Keshab talks only to you.

## 1. Pair with GitHub — once per session
DST=/home/user/agent-bootstrap
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect
# ALREADY CONNECTED হলে কিছুই করতে হবে না; code দেখালে একবার approve করো।
# turn শেষ হয়ে গেলে: python3 "$DST/device_pair.py" poll 60

## 2. Read your playbook — it lives in the clone you just made
cat /home/user/agent-bootstrap/captain/CAPTAIN_PROMPT.md
# সেটাই follow করো। শেষ হলে শুধু লেখো: Captain ready — কাজ বলো।
```

**গুরুত্বপূর্ণ:** এখানে পুরো playbook লেখা নেই, কেবল **link** — কারণ agent নিজেই clone
থেকে `captain/CAPTAIN_PROMPT.md` পড়ে নেবে। তাই প্রথম paste টা ছোট (১০ লাইন), আর
playbook update করলে সব agent নতুনটাই পাবে।

**কোথায় পাবে:** রেপোতে `CAPTAIN_START_PROMPT.md` · copy পেজে `PROMPT_COPY.html`
("⚡ Captain — one paste" বাটন)। হাতে হাতে চাইলে:
`https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/CAPTAIN_START_PROMPT.md`

## ধাপ ২ — কাজটা বলো (একই Captain চ্যাটে)

এখন স্বাভাবিক বাংলায় বলো কী করতে চাও। যা বললে ভালো হয়: **কোন repo + কী সমস্যা/কী চাই**।
উদাহরণ — হুবহু এভাবে লিখতে পারো:

```text
Batch 1 বানাও:
1) docify — home screen 360px ফোনে overflow করছে, ঠিক করতে হবে
2) quizbaaz — results screen-এ player list-এ tap করলে কোনো feedback নেই
3) flutter-builder — README-র বাংলা অংশে একটা বানান ভুল আছে

তিনটা আলাদা brief (A/B/C) লিখে দাও, কোনটা কোন চ্যাটে দেব সেটাও লিখো।
```

Captain কাজটা ভেঙে **তিনটা ভরা brief** লিখে দেবে — আর প্রতিটার সাথে বলবে কোন চ্যাটে দিতে হবে।
কোন ফাইল কে ধরবে, কোনটা কেউ ছুঁবে না (`DO NOT TOUCH`), আর কোন check চালাবে — সব ওই brief-এ লেখা থাকবে।

---

## ধাপ ৩ — Worker চ্যাটগুলো (৩টা আলাদা নতুন chat)

Captain যেই A/B/C brief দেবে, প্রতিটা **আলাদা নতুন agent chat**-এ paste করো।
(একই চ্যাটে দুইটা brief দিও না — তাহলে দুইজনের সময় ভাগ হয়ে যাবে, parallel থাকবে না।)

প্রতিটা worker চ্যাটও প্রথমবার একটা code দেখাবে → সেটাও approve করে দাও।
ওরা নিজের branch-এ (`agent/A/…`, `agent/B/…`, `agent/C/…`) কাজ করে push করবে, শেষে
এমন একটা ব্লক ফেরত দেবে:

```text
AGENT A DONE
branch: agent/A/home-overflow
sha: 4f2c1ab
check: flutter test test/home_screen_test.dart → pass
changed: header row Flexible করা হয়েছে
not touched: theme, pubspec, workflows
blocked: none
```

---

## ধাপ ৪ — ফেরত Captain-এর কাছে

ওই `AGENT A DONE` ব্লকগুলো (তিনটা) কপি করে Captain চ্যাটে paste করো:

```text
AGENT A DONE
[ব্লকটা paste]

AGENT B DONE
[ব্লকটা paste]

AGENT C DONE
[ব্লকটা paste]
```

অথবা এতটুকুই লিখো:

```text
A, B, C তিনজনই push করেছে — তুমি git fetch করে নিজেই দেখে নাও।
```

Captain নিজেই `git diff main...origin/agent/A/…` দেখে নিতে পারে — তাই report paste করা
আবশ্যক নয়, শুধু সুবিধার জন্য।

---

## ধাপ ৫ — Captain merge করে, তোমাকে জানায়

Captain: diff পড়ে → ছোট খুঁজে ঠিক করে → merge → `main`-এ push → ৫ লাইনের report দেয়:

```text
Batch 1: A merged (4f2c1ab), B merged (9d10e77), C তে conflict — থামিয়ে দিয়েছি
Changed: home overflow fix; results screen-এ tap feedback
Evidence: preflight ok; A/B/C diff scope clean
Not touched: pubspec, workflows, android/
Next: batch 2 — তুমি বলো
```

**tag / release / secret / workflow বদলাতে হলে Captain আগে তোমাকে জিজ্ঞেস করবে** — এটা
ওর prompt-এ লেখা আছে, তাই ট্যাগ সবসময় তোমার হাতেই থাকে।

---

## পুরো ছবিটা

```text
তুমি ──► CAPTAIN চ্যাট ──brief A/B/C──► worker A / B / C চ্যাট
                                            │ (নিজের branch, নিজের sandbox)
                                            ▼
 তুমি ◄── Captain: merge + report ◄── "AGENT X DONE" ব্লক (তুমি paste করো)
              │
              └──► main-এ push (tag নয় — tag তোমার হাতে)
```

---

## এখন সব কিছু repo-তে — কোথায় কী

| ফাইল | কী | কে পড়ে |
|---|---|---|
| `CAPTAIN_START_PROMPT.md` | প্রথম paste (১০ লাইন) | Captain-কে তুমি paste করো |
| `captain/CAPTAIN_PROMPT.md` | Captain-এর পুরো playbook | Captain নিজে পড়ে |
| `captain/WORKER_BRIEF_TEMPLATE.md` | brief template | Captain ভরে worker-কে দেয় |
| `captain/examples/*.md` | ভরা ৩টা brief (A/B/C) | দৃষ্টান্ত, repo-তেই থাকে |
| `captain/HOW_TO_START_BN.md` | এই ফাইল | তোমার জন্য |

## নতুন session শুরু হলেও যা লাগবে না

- কিছু ইত্যাদি মনে রাখতে হবে না — `agent-captain-kit/` ফোল্ডারটা workspace-এ থেকে যায়।
- GitHub token নিজে লাগবে না — Captain আগে থেকেই pair করা থাকে
  (`/home/user/agent-bootstrap/secrets/gh_token.txt`, ~৮ ঘণ্টা, auto-refresh)।
- নতুন worker চ্যাট করলে **পুরোনো কিছু** লাগে না — শুধু তার brief টা।

## যদি খুব দ্রুত দরকার হয় (Short version)

পুরো playbook paste করার দরকার নেই — উপরের ১০ লাইনের version টাই যথেষ্ট।
একেবারে minimum চাইলে এটুকু দিলেও Captain নিজে repo থেকে বাকিটা পড়ে নেবে:

```text
তুমি আমার Captain (main agent)। আমি Keshab1997 — তুমিই আমার সাথে কথা বলবে।

নিয়ম: কাজ ভেঙে worker A/B/C-কে brief দেবে; ওরা নিজের branch-এ push করবে, main-এ না;
তুমি diff পড়ে check-fix-merge করে main-এ push করবে; tag/release/secret কখনো নিজে করবে না —
আমাকে জিজ্ঞেস করবে। worker-দের ভারী check চালাবি না, শুধু preflight.py / pytest -q।

প্রথমে: /home/user/agent-bootstrap clone করে pair হও (ALREADY CONNECTED হলে skip),
তারপর আমাকে জিজ্ঞেস করো কী কাজ। প্রতিটা worker brief-এ Goal, কোন ফাইল ওর,
কার কোনটা DO NOT TOUCH, কোন check, আর report format — সব লিখে দেবে।
```
