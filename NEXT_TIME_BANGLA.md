# 🔖 পরেরবার কী করব — কম authorization, একই starter

**Repo:** https://github.com/Keshab1997/agent-bootstrap
**App:** `keshab-flutter-assistant` · **Account:** Keshab1997

## সবচেয়ে সহজ পথ

Captain-এর নতুন চ্যাটে [`CAPTAIN_START_PROMPT.md`](CAPTAIN_START_PROMPT.md) দিন,
তারপর কোন repo-তে কী কাজ চান বলুন। একই Captain workspace ব্যবহার চালিয়ে গেলে
সেভ করা login-টাই কাজে লাগবে।

শুধু একজন agent দিয়ে কাজ হলে [`AGENT_START_PROMPT.md`](AGENT_START_PROMPT.md)
বা [`PROMPT-FOR-NEW-AGENT.txt`](PROMPT-FOR-NEW-AGENT.txt) দিন।

একদম ছোট করে বললেও চলে:

```text
https://github.com/Keshab1997/agent-bootstrap clone করো
/home/user/agent-bootstrap-এ। python3 gh_app.py connect চালিয়ে আগে saved
session restore করো। ALREADY CONNECTED হলে কিছু চাইবে না; code দেখালেই শুধু
আমাকে দেবে। turn শেষ হলে একই code-এ device_pair.py poll 60 দিয়ে resume করো।
```

## এখন কীভাবে কাজ করে

```text
সেভ করা token কাজ করছে? → সরাসরি কাজ
         ↓ না
সেভ করা refresh দিয়ে ঠিক হলো? → সরাসরি কাজ, browser লাগবে না
         ↓ না; credential সত্যিই নেই/বাতিল
আগের pending code এখনও বেঁচে আছে? → সেই code-ই resume
         ↓ না
তখনই নতুন code → একবার browser-এ অনুমোদন
```

Network error, GitHub-এর সাময়িক সমস্যা বা rate limit হলে **retry** করবে;
ওগুলোকে নতুন authorization লাগার প্রমাণ হিসেবে ধরবে না।

## Code দেখালে শুধু তখন

1. https://github.com/login/device খুলুন।
2. দেখানো `XXXX-XXXX` code দিন → **Continue**।
3. App-এর নাম `keshab-flutter-assistant` এবং permissions দেখে **Authorize** করুন।

Code প্রায় ১৫ মিনিট বৈধ। Agent এবার code দেখানোর **আগেই** সেটি সেভ করে।
আপনি approve করার আগে/পরে turn শেষ হলেও নতুন code দরকার নেই:

```bash
python3 /home/user/agent-bootstrap/device_pair.py poll 60
```

`TIMEOUT for this turn` মানে ৬০ সেকেন্ডের অপেক্ষা শেষ, code শেষ নয়। একই command
আবার চলবে। সত্যিই `EXPIRED` হলে `gh_app.py connect` নতুন code নিতে পারে।

## Workers: একই চ্যাট ব্যবহার, সরাসরি branch push

Captain A/B/C-কে brief দেবে। সম্ভব হলে প্রত্যেক worker-এর একই চ্যাট/workspace
বারবার ব্যবহার করুন। প্রথমবার approval লাগতে পারে; পরের batch-এ saved login
ও refresh reuse হবে।

Worker নিজের `agent/A|B|C/...` branch push করবে। Captain-কে শুধু বলুন
**“A/B/C push করেছে, fetch করে দেখে নাও”**। কোনো ফাইল download/upload লাগবে না।
Captain diff পড়ে, check করে, `main`-এ merge/push করবে।

Private repo-তেও worker-এর নিজস্ব অনুমোদিত access ব্যবহার হবে। Token কখনো
এক agent থেকে অন্যজনকে কপি হবে না। নতুন workspace বা revoked/lost credentials
হলে আবার approval লাগতে পারে।

## Authenticator-এর GitHub code দিলে কি হবে?

ওই ৬-digit code account login-এর **2FA**। Agent যে `XXXX-XXXX` device code
দেখায়, সেটি আলাদা app-access request। একটির জায়গায় অন্যটি ব্যবহার করা যায়
না; authenticator code API token-ও নয়। GitHub login পেজে 2FA চাইলে সেখানে
দেবেন—agent chat-এ code, authenticator seed বা recovery code পাঠাবেন না।

## পুরোনো clone থাকলে একবার update

নিজের local edit না থাকলে:

```bash
cd /home/user/agent-bootstrap
git pull --ff-only
python3 gh_app.py connect
```

Update আটকে গেলে local edit বা `secrets/` মুছবেন না। Agent-কে সমস্যাটা দেখুন বলুন।
নতুন clone সরাসরি নতুন code-টাই পাবে। PAT/private key/server সেটআপ লাগবে না।

## দরকারি command

```bash
python3 gh_app.py connect              # reuse → refresh → resume → দরকার হলে pair
python3 gh_app.py connect --show-only  # code সেভ/পুনর্ব্যবহার; poll না করে exit
python3 gh_app.py status               # check/refresh; নতুন code কখনো নেবে না
python3 device_pair.py status          # pending code-এর বাকি সময়, offline
python3 device_pair.py poll 60         # একই code resume
python3 selftest.py                    # fake token দিয়ে offline regression tests
```

`PAIRED` = কাজ করা যাবে। `UNCONFIRMED` = পরে retry, নতুন approval নয়।
`NOT PAIRED` = `connect` চালান; সেটি কী বলে দেখুন।

## কতদিন চলবে — সীমাটা পরিষ্কার

| জিনিস | আচরণ |
|---|---|
| Access token | সাধারণত ৮ ঘণ্টা; valid refresh থাকলে browser ছাড়াই নতুন token |
| Refresh token | সাধারণত ১৮১ দিনের মেয়াদ; ব্যবহারে rotate হয়, নতুনটি সেভ হয় |
| একই workspace-এর পরের turn | সেভ করা session/pending code reuse হয় |
| একদম নতুন Captain workspace | পুরোনো credential নেই — প্রথম approval এখনও দরকার |
| একই worker workspace-এর পরের batch | saved login/refresh reuse; branch push দিয়ে handoff |
| Revoked/expired refresh বা হারানো credential | আবার approval লাগতে পারে |

**শুধু public repo দিয়ে সব নতুন workspace-কে গোপনে write access দেওয়া নিরাপদ নয়।**
তার জন্য আলাদা secure credential-delivery ব্যবস্থা লাগবে; এই update তা বানায় না।
`vault.py` ব্যবহার করলেও তার password নিরাপদে দেওয়ার ব্যবস্থা চাই।

## নিরাপত্তা ও Flutter

- `secrets/`, token, refresh token, private key বা vault password git/chat/worker
  brief-এ দেবেন না। এক agent-এর refresh token আরেকজনকে কপি করবেন না।
- `/home/user/agent-bootstrap` একই workspace-এ রাখুন; নতুন workspace নিজে থেকে
  পুরোনো workspace-এর credentials পায় না।
- Flutter/Dart কাজ হলে starter prompt-এর SDK ও cheap-check নিয়ম মানুন।
  Authorization ঠিক করতে Flutter install/build বা CI চালানোর দরকার নেই।
- Access বন্ধ করতে GitHub-এর App settings থেকে revoke/uninstall করুন;
  নতুন authorization না হওয়া পর্যন্ত আর access থাকবে না।
