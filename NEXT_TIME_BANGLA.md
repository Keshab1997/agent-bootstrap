# 🔖 পরেরবার কী করব — Cheat Sheet

**Repo:** https://github.com/Keshab1997/agent-bootstrap
**এই cheat sheet-এর সরাসরি লিংক:** https://github.com/Keshab1997/agent-bootstrap/blob/main/NEXT_TIME_BANGLA.md
**Raw (কপি করার সুবিধার্থে):** https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/NEXT_TIME_BANGLA.md
**App:** `keshab-flutter-assistant` · **Account:** Keshab1997

---

## ✅ সবচেয়ে সহজ উপায় (৯০% সময় এটাই)

যেকোনো AI agent-এর চ্যাটে গিয়ে **শুধু এই লাইনটা paste করুন**:

```
Clone https://github.com/Keshab1997/agent-bootstrap and follow its README.md to
connect to my GitHub via device flow. Then run: python3 gh_app.py connect
Show me the 8-character code clearly and wait until I approve it in my browser.
```

বাংলায় লিখলেও চলবে:

```
https://github.com/Keshab1997/agent-bootstrap clone করে README.md অনুযায়ী
আমার GitHub-এ device flow দিয়ে connect হও। python3 gh_app.py connect চালাও,
আমাকে ৮-অক্ষরের code টা দেখাও, আর আমি browser-এ approve না করা পর্যন্ত অপেক্ষা করো।
```

### 🐦 Flutter/Dart project হলে — এই ভার্সনটাই paste করুন (একবারেই সব)

```
Clone https://github.com/Keshab1997/agent-bootstrap and follow its README.md to
connect to my GitHub via device flow. Then run: python3 gh_app.py connect
Show me the 8-character code clearly and wait until I approve it in my browser.
Then, since this is a Flutter project, also run bash <(curl -fsSL
https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh)
--quiet --json to give yourself a Flutter SDK, and run flutter pub get,
flutter analyze and flutter test on <repo/path>.
```

বাংলায়:

```
agent-bootstrap দিয়ে আমার GitHub-এ connect হও (device flow, ৮-অক্ষরের code দেখাও,
আমি approve করা পর্যন্ত অপেক্ষা করো)। এটা Flutter project, তাই তারপর
flutter-bootstrap-এর setup.sh চালিয়ে নিজের sandbox-এ Flutter SDK বসাও,
তারপর <repo/path>-এ flutter pub get, flutter analyze আর flutter test চালাও।
```

### তারপর আপনার কাজ মাত্র ৩টা ক্লিক

| ধাপ | কী করবেন | সময় |
|---|---|---|
| 1️⃣ | Agent যে লিংকটা দেখাবে সেটা খুলুন → **https://github.com/login/device** | ৫ সেকেন্ড |
| 2️⃣ | Agent যে `XXXX-XXXX` code দেখাবে সেটা টাইপ করে **Continue** | ১০ সেকেন্ড |
| 3️⃣ | **Authorize** চাপুন | ১ সেকেন্ড |

**ব্যস।** Agent নিজে থেকেই token ধরে ফেলবে, save করবে, আর কাজ শুরু করে দেবে।

> ⏱️ Code টা **১৫ মিনিট** valid। সময় পার হয়ে গেলে agent-কে বলুন
> *"নতুন code দাও"* — ও আবার generate করে দেবে। কোনো ক্ষতি নেই।

---

## 🖥️ নিজে হাতে করতে চাইলে (terminal থেকে)

```bash
git clone https://github.com/Keshab1997/agent-bootstrap.git
cd agent-bootstrap
python3 gh_app.py connect
# → code টা বের হবে → browser-এ approve করুন
```

অথবা এক লাইনে:

```bash
curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/setup.sh | bash
```

**GitHub + Flutter একসাথে** (Flutter/Dart project-এ কাজ করলে):

```bash
curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/setup.sh \
  | bash -s -- --with-flutter
```

Flutter-এর জন্য আলাদা করে চালাতে চাইলে:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh)
```

⏱️ Flutter SDK নামতে ~৪০ সেকেন্ড লাগে, আর ওটা ২.৫ GB — তাই যেটা লাগে শুধু সেটাই চালান।
Flutter setup ব্যর্থ হলেও GitHub connection ঠিক থাকে।

দরকারি কমান্ড:

```bash
python3 gh_app.py status          # connection ঠিক আছে কিনা
python3 gh_app.py whoami          # কে login হলো
python3 gh_app.py repos           # repo লিস্ট
python3 gh_app.py api GET /user   # যেকোনো REST call
python3 gh_app.py revoke          # connection বিচ্ছিন্ন
```

কোনো `pip install` লাগবে না — শুধু python3 থাকলেই হবে।

---

## 📱 ফোনে রাখার মতো একদম ছোট ভার্সন

> **agent কে বলো:** `Keshab1997/agent-bootstrap` clone করে README অনুযায়ী connect হও
> **আমি করব:** github.com/login/device → code টাইপ → Authorize

---

## ⏰ কতদিন চলবে?

| জিনিস | মেয়াদ |
|---|---|
| Device code | ১৫ মিনিট (approve না করলে নিজে থেকেই মরে যাবে, ক্ষতি নেই) |
| Access token (`ghu_…`) | **৮ ঘণ্টা** — একটা কাজের session-এর জন্য যথেষ্ট |
| Auto-refresh | ৮ ঘণ্টা শেষ হওয়ার আগে `gh_app.py` নিজে থেকে refresh করে নেয় |
| Refresh token | **১৮১ দিন** — এই সময়ের মধ্যে code ছাড়াই চলবে |
| ১৮১ দিন পরে | আবার একবার device flow (৩ ক্লিক) |

**মানে:** একবার connect করলে সেই sandbox/session যতক্ষণ বাঁচে ততক্ষণ চলবে।
নতুন sandbox = নতুন ৩ ক্লিক। এটাই ইচ্ছাকৃত — নিরাপত্তার জন্য।

---

## 🚨 সমস্যা হলে

| লক্ষণ | সমাধান |
|---|---|
| `HTTP 401` / `Bad credentials` | `python3 gh_app.py connect` আবার চালান |
| `expired_token` | code টা ১৫ মিনিট পার হয়ে গেছে — নতুন code নিন |
| `access_denied` | browser-এ Cancel চেপে ফেলেছেন — আবার করুন |
| Agent code দেখাচ্ছে না | উপরের paste-করা লাইনটাই হুবহু দিন |
| Agent repo clone করতে পারছে না | agent-কে বলুন raw URL ব্যবহার করতে: `https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/gh_app.py` |

**সব কিছু একসাথে বন্ধ করতে:**
GitHub → Settings → Applications → Installed GitHub Apps →
`keshab-flutter-assistant` → **Uninstall**
(এটা করলে সব token সাথে সাথেই বাতিল হয়ে যাবে)

---

## 🐦 Flutter নিয়ে ৩টা কথা

1. **Sandbox-এ Flutter আগে থেকে থাকে না**, আর install করা SDK পরের session-এ
   মুছে যায় — তাই প্রতিবার ~৪০ সেকেন্ডে আবার বসাতে হয় (`flutter-bootstrap` এর
   কাজ এটাই)।
2. **`--with-flutter` দিলে একবারেই দুটো কাজ** — GitHub connect + Flutter SDK।
   Flutter না লাগলে দেবেন না (২.৫ GB)।
3. **Install হওয়ার পর `flutter analyze`, `flutter test` সরাসরি লিখলেই চলে** —
   আলাদা করে PATH সেট করতে হয় না। বিস্তারিত: `flutter-bootstrap`-এর
   `NEXT_TIME_BANGLA.md`।

---

## 🔒 মনে রাখার মতো ৩টা কথা

1. **Repo-তে কোনো password/token নেই** — তাই public হলেও বিপদ নেই। কেউ clone
   করলে শুধু স্ক্রিপ্ট পাবে, আপনার account-এ ঢুকতে গেলে আপনার browser-এর
   Authorize লাগবেই।
2. **Agent-কে কখনো নিজের GitHub password বা টোকেন টাইপ করে দেবেন না।** এই
   পুরো ব্যবস্থাটাই বানানো হয়েছে যাতে সেটা না লাগে।
3. **নতুন device code দেখালে approve করার আগে দেখে নিন** App-এর নাম
   `keshab-flutter-assistant` কিনা। অন্য কিছু দেখালে Authorize চাপবেন না।

---

*এই ফাইলটা: https://github.com/Keshab1997/agent-bootstrap/blob/main/NEXT_TIME_BANGLA.md · তৈরি: 2026-09-25*
