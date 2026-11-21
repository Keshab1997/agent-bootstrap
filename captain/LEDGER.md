# Captain ledger — `LEDGER.json`

Machine-readable batch state, so a fresh Captain session resumes in one
command instead of re-reading chat history. It mirrors the Fast Lane ledger
columns ([FASTLANE.md §3](FASTLANE.md#3-captain-verify-review-then-assign-the-next-task)):
`repo | batch | worker | task | brief_sha/url | tracker | branch | base_sha |
sha | status | integration_sha | history`.

## Rules

- **`captain/LEDGER.json` is `.gitignored`.** Batch state can name private
  repos; it never enters the public bootstrap repo. `LEDGER.example.json`
  shows the schema.
- **GitHub is the source of truth.** The ledger is a cache of what the
  Captain has verified. Reconcile with `python3 captain/batch_status.py`
  (compares every ledger sha against the live `arena/*` tips, checks tracker
  mentions and the latest CI runs). A tip that moved past the ledger means an
  unreviewed checkpoint — diff `base..tip` and run CI on that branch before
  trusting it.
- One entry per live worker task (`repo`+`batch`+`worker`+`task` is the
  key). Checkpoints accumulate in `history`; never edit `history` by hand.
- Statuses: `assigned → pushed → verified → review → landed`, plus
  `blocked` / `bounced`. Record `integration_sha` when the change lands on
  `main`.
- **Record by hand:** add the checkpoint with `ledger.py checkpoint` right after
  you verify the branch, and `--status landed --integration-sha …` when it lands.

## Commands

```bash
# assign (right after publishing the pinned brief)
python3 captain/ledger.py upsert --repo Keshab1997/docify --batch b1 \
  --worker A --task home-refresh --branch arena/xyz \
  --brief-sha <40hex> --brief-url <permalink> --tracker <issue url|"worker chat"> \
  --base-sha <40hex|null>

# on check-in / verification / landing
python3 captain/ledger.py checkpoint --repo Keshab1997/docify --batch b1 \
  --worker A --task home-refresh --sha <pushed 40hex> --status verified
python3 captain/ledger.py checkpoint ... --status landed --integration-sha <main sha>

# read
python3 captain/ledger.py show [--repo R] [--batch B] [--json]
```

## Fresh-session resume

```bash
bash captain_up.sh                       # pair + ff-pull + playbook
python3 captain/ledger.py show           # what was in flight
python3 captain/batch_status.py          # live GitHub state vs. ledger
```

If `LEDGER.json` is missing (new sandbox), `batch_status.py` still lists
every `captain/briefs/*` and `arena/*` ref per repo — rebuild entries from
the pinned briefs with `ledger.py upsert`.
