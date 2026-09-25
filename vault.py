#!/usr/bin/env python3
"""
vault.py -- optional encrypted store for a token (e.g. a Fine-Grained PAT).

By default this repo holds NO credentials. This file exists only for the case
where you later decide you want a "paste one line, get instant access" setup.

    python3 vault.py seal   --passphrase-file ~/pw.txt --set token
    python3 vault.py unseal --passphrase-file ~/pw.txt --get token
    python3 vault.py verify --passphrase-file ~/pw.txt
    python3 vault.py list

Crypto (stdlib + openssl only, nothing to pip install):

    passphrase --PBKDF2-HMAC-SHA256 (600k iters, 16-byte random salt)--> 64 B
        first  32 B -> AES-256-CBC encryption key   (openssl enc, random IV)
        second 32 B -> HMAC-SHA256 authentication key
    encrypt-then-MAC. Opening checks the HMAC first, so a wrong passphrase or
    a tampered file fails cleanly instead of producing garbage.

Output is base64 text with no magic bytes -- GitHub secret scanning never
flags it, and it is safe to commit to a private *or* public repository.
The passphrase is the only thing that must stay secret. Keep it OUT of git.

WHY A PAT AND NOT THE APP REFRESH TOKEN:
    GitHub App refresh tokens rotate on every use. If two agents share one,
    the first to refresh kills it for the other. A Fine-Grained PAT
    (github_pat_...) does not rotate, so it is the only credential that works
    for a shared/static vault. Create one at:
    GitHub -> Settings -> Developer settings -> Personal access tokens
            -> Fine-grained tokens -> Generate new token
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import subprocess
import sys

VERSION = 1
KDF = "pbkdf2-hmac-sha256"
KDF_ITERATIONS = 600_000
CIPHER = "aes-256-cbc"
MAC = "hmac-sha256"
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.json")


# --------------------------------------------------------------------------- #
# crypto
# --------------------------------------------------------------------------- #
def _derive(passphrase: str, salt: bytes) -> tuple[bytes, bytes]:
    material = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, KDF_ITERATIONS, dklen=64)
    return material[:32], material[32:]


def _openssl(mode: str, key: bytes, iv: bytes, data: bytes) -> bytes:
    """aes-256-cbc through the openssl CLI (KDF done by us, so -nosalt)."""
    proc = subprocess.run(
        ["openssl", "enc", f"-{CIPHER}", f"-{mode}", "-nosalt",
         "-K", key.hex(), "-iv", iv.hex()],
        input=data, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"openssl failed: {proc.stderr.decode(errors='replace')[:200]}")
    return proc.stdout


def encrypt_blob(plaintext: bytes, passphrase: str) -> dict:
    salt = os.urandom(16)
    iv = os.urandom(16)
    enc_key, mac_key = _derive(passphrase, salt)
    ciphertext = _openssl("e", enc_key, iv, plaintext)
    body = {
        "version": VERSION,
        "kdf": KDF,
        "iterations": KDF_ITERATIONS,
        "cipher": CIPHER,
        "mac": MAC,
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "data": base64.b64encode(ciphertext).decode(),
    }
    signing_input = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["hmac"] = base64.b64encode(
        hmac.new(mac_key, signing_input, hashlib.sha256).digest()).decode()
    return body


def decrypt_blob(body: dict, passphrase: str) -> bytes:
    if body.get("version") != VERSION:
        raise SystemExit(f"unsupported vault version: {body.get('version')}")
    if body.get("kdf") != KDF or body.get("cipher") != CIPHER or body.get("mac") != MAC:
        raise SystemExit(f"unsupported vault algorithms: {body.get('kdf')}/{body.get('cipher')}")
    if body.get("iterations", 0) < 100_000:
        raise SystemExit("vault iterations suspiciously low -- refusing")

    mac_b64 = body.pop("hmac", None)
    if not mac_b64:
        raise SystemExit("vault has no HMAC -- refusing to open")
    salt = base64.b64decode(body["salt"])
    iv = base64.b64decode(body["iv"])
    ciphertext = base64.b64decode(body["data"])

    enc_key, mac_key = _derive(passphrase, salt)
    signing_input = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(mac_key, signing_input, hashlib.sha256).digest()
    try:
        provided = base64.b64decode(mac_b64)
    except binascii.Error:
        raise SystemExit("vault HMAC is malformed") from None
    if not hmac.compare_digest(expected, provided):
        raise SystemExit("AUTHENTICATION FAILED: wrong passphrase or tampered file")
    return _openssl("d", enc_key, iv, ciphertext)


# --------------------------------------------------------------------------- #
# storage
# --------------------------------------------------------------------------- #
def load_vault(path: str) -> dict:
    if not os.path.exists(path):
        return {"schema": "agent-bootstrap-vault", "entries": {}}
    with open(path) as fh:
        v = json.load(fh)
    v.setdefault("schema", "agent-bootstrap-vault")
    v.setdefault("entries", {})
    return v


def save_vault(path: str, vault: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(vault, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o644)   # ciphertext; readable is fine
    except OSError:
        pass


def read_passphrase(args) -> str:
    if getattr(args, "passphrase", None):
        return args.passphrase
    if getattr(args, "passphrase_file", None):
        with open(os.path.expanduser(args.passphrase_file)) as fh:
            return fh.read().strip()
    env = os.environ.get("VAULT_PASSPHRASE")
    if env:
        return env
    try:
        import getpass
        return getpass.getpass("vault passphrase: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nno passphrase supplied")


def strength_note(pw: str) -> str:
    """Cheap advisory -- never refuses, just warns."""
    import math
    pool = 0
    if any(c.islower() for c in pw):
        pool += 26
    if any(c.isupper() for c in pw):
        pool += 26
    if any(c.isdigit() for c in pw):
        pool += 10
    if any(not c.isalnum() for c in pw):
        pool += 33
    bits = len(pw) * math.log2(pool) if pool and pw else 0
    if bits < 60:
        return (f"  ! passphrase entropy ~{bits:.0f} bits -- weak. "
                f"Consider 4+ random words or 20+ random characters.")
    return f"  passphrase entropy ~{bits:.0f} bits"


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_seal(args) -> int:
    pw = read_passphrase(args)
    if args.generate_passphrase:
        pw = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
        print("generated passphrase (SAVE IT, shown once):")
        print(f"  {pw}")
    print(strength_note(pw))

    vault = load_vault(args.file)
    if args.value is not None:
        plaintext = args.value.encode()
    elif args.stdin:
        plaintext = sys.stdin.read().strip().encode()
    else:
        plaintext = sys.stdin.read().strip().encode()
    if not plaintext:
        raise SystemExit("nothing to seal (empty value)")

    vault["entries"][args.set] = encrypt_blob(plaintext, pw)
    save_vault(args.file, vault)
    print(f"sealed '{args.set}' ({len(plaintext)} bytes) -> {args.file}")
    print(f"  cipher={CIPHER} kdf={KDF} iters={KDF_ITERATIONS}")
    return 0


def cmd_unseal(args) -> int:
    pw = read_passphrase(args)
    vault = load_vault(args.file)
    if args.get not in vault["entries"]:
        raise SystemExit(f"no entry named '{args.get}' in {args.file}")
    plaintext = decrypt_blob(dict(vault["entries"][args.get]), pw)
    if args.to_file:
        path = os.path.expanduser(args.to_file)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(plaintext.decode() + "\n")
        print(f"wrote {path} (chmod 600)", file=sys.stderr)
    else:
        sys.stdout.write(plaintext.decode() + "\n")
    return 0


def cmd_verify(args) -> int:
    pw = read_passphrase(args)
    vault = load_vault(args.file)
    if not vault["entries"]:
        print(f"{args.file}: vault is empty (no credentials stored)")
        return 0
    ok = bad = 0
    for name, blob in vault["entries"].items():
        try:
            decrypt_blob(dict(blob), pw)
            print(f"  OK   {name}")
            ok += 1
        except SystemExit:
            print(f"  FAIL {name} (wrong passphrase or tampered)")
            bad += 1
    print(f"\n{ok} verified, {bad} failed")
    return 0 if not bad else 1


def cmd_list(args) -> int:
    vault = load_vault(args.file)
    if not os.path.exists(args.file):
        print(f"{args.file} does not exist yet -- vault is unused.")
        return 0
    if not vault["entries"]:
        print(f"{args.file}: empty vault (no credentials stored)")
        return 0
    print(f"{args.file}:")
    for name, blob in vault["entries"].items():
        raw = base64.b64decode(blob["data"])
        print(f"  {name:<16} {len(raw)} bytes ciphertext  "
              f"kdf={blob.get('kdf')} iters={blob.get('iterations')}")
    return 0


def cmd_forget(args) -> int:
    vault = load_vault(args.file)
    if args.name in vault["entries"]:
        del vault["entries"][args.name]
        save_vault(args.file, vault)
        print(f"removed '{args.name}'")
    else:
        print(f"'{args.name}' not present")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="vault.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", default=DEFAULT_FILE, help="vault file (default vault.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_pw(sp):
        sp.add_argument("--passphrase")
        sp.add_argument("--passphrase-file", help="file containing the passphrase")

    s = sub.add_parser("seal", help="encrypt a value into the vault")
    s.add_argument("--set", required=True, help="entry name, e.g. token")
    s.add_argument("--value", help="value (else read from stdin)")
    s.add_argument("--stdin", action="store_true")
    s.add_argument("--generate-passphrase", action="store_true")
    add_pw(s)
    s.set_defaults(f=cmd_seal)

    u = sub.add_parser("unseal", help="decrypt an entry")
    u.add_argument("--get", required=True, help="entry name")
    u.add_argument("--to-file", help="write to this path (chmod 600) instead of stdout")
    add_pw(u)
    u.set_defaults(f=cmd_unseal)

    v = sub.add_parser("verify", help="check the passphrase opens every entry")
    add_pw(v)
    v.set_defaults(f=cmd_verify)

    sub.add_parser("list", help="list entries (names only, no secrets)").set_defaults(f=cmd_list)

    fo = sub.add_parser("forget", help="delete an entry")
    fo.add_argument("name")
    fo.set_defaults(f=cmd_forget)

    args = p.parse_args()
    return args.f(args)


if __name__ == "__main__":
    raise SystemExit(main())
