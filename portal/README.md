# Submission forms

`MakeForms.gs` creates one Google Form per deliverable, D-1 to D-14.

## Why forms and not the Apps Script portal

The portal identifies students with `Session.getActiveUser().getEmail()`. On a
**personal** Google account that returns an empty string for anyone outside the
owner's domain, so the roster never matches and submissions cannot be
attributed. That is a documented Apps Script privacy restriction.

A Forms **file-upload question requires the respondent to sign in**, and the
response records the account they used. So this works on a personal account,
today, with no migration.

## Install

1. Open <https://script.google.com> and sign in as the course owner.
2. **New project** (or open the existing `AM5061 Portal` project).
3. Rename it `AM5061 Forms` if it is new.
4. Click **+** next to Files → **Script** → name it `MakeForms`.
5. Copy `MakeForms.gs` from this folder and paste it in, replacing whatever is there.
6. Save (⌘S / Ctrl+S).

## Run

1. In the function dropdown at the top, select **`makeAllForms`**.
2. Click **Run**.
3. Authorise when prompted. It will warn the app is unverified — this is your
   own script: **Advanced → Go to AM5061 Forms (unsafe)** → **Allow**.
4. Open **Execution log** (bottom panel). The 14 form links are printed there.

Re-running is safe: it skips any deliverable whose form already exists.

## What it creates

```
AM5061 Jul-Nov 2026/
├── 00_Admin/
│   └── AM5061 Submissions (Forms)      ← one tab per deliverable
└── 06_Submissions/
    └── _Forms/                          ← the 14 form files
```

Student uploads land in your Drive. Students cannot see each other's work.

## Afterwards

| Function | Does |
|---|---|
| `closeForm('D-6')` | stops accepting responses after the deadline |
| `whoIsMissing('D-6')` | lists roll numbers with no submission, using the Roster tab |

Set a deadline on each form in the form editor: **Settings → Responses →
Accepting responses**, or just run `closeForm` when the time comes.

## If something errors

| Error | Fix |
|-------|-----|
| `setMaxFileSize` rejects the value | Google accepts only fixed sizes. Change to `1024*1024*1024` (1 GB) or drop the line for the default. |
| `setCollectEmail is not a function` | Newer Forms API. Replace with `.setEmailCollectionType(FormApp.EmailCollectionType.VERIFIED)`. |
| `Course folder not found` | The folder name at the top of the script must match your Drive exactly. |

**Test it before you announce it.** Submit once from a Google account that is
not yours and check the recorded email is the real one.
