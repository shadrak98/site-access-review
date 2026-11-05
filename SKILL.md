---
name: site-access-review
description: Count enabled system and website users on a Frappe site who are ex-employees or ex-interns (per Employee and Intern records on frappe.io), and audit their activity after their relieving date (logins, downloads, exports, changes, deletions) over the past year. Use when the user asks for an access review, a leaver or offboarding audit, "who still has access to <site>", or whether ex-employees logged in, exported or deleted data on a site such as support, press, crm or insights.
---

# Site access review

Read-only review of one Frappe site, driven by `frappectl`. Takes the **site name** (a `frappectl` profile) as its parameter.

## Quick start

```bash
python3 ~/.claude/skills/site-access-review/scripts/review.py --site <profile> [--hr-site <profile for https://frappe.io>] [--days 365]
```

Writes `access-review-<profile>.md` to the current directory. Run from the directory where the report should go. A large site (Press) can take several minutes, so run it in the background.

## Prerequisite: frappe.io profile

Employee and Intern records on **https://frappe.io** are the source of truth. Before anything else, confirm `frappectl auth list` has a profile whose site is `https://frappe.io` and that it still works (`frappectl -s <profile> api method/frappe.client.get_count -F doctype=Employee`). If it is missing or expired, stop and ask the user to run `! frappectl auth login https://frappe.io`. Do not run auth commands yourself. The script checks this itself and exits with the same instruction.

## Workflow

1. **Resolve the site.** Run `frappectl auth list` and match the user's site name to a profile. If two profiles share a site or none match, ask. Never guess.
2. **Check access** to that site with `frappectl -s <profile> api method/frappe.client.get_count -F doctype=User`. On an OAuth error, ask the user to run `! frappectl auth login https://<host>`, then run `frappectl auth list` again, because login can create a new profile name. Use that one.
3. **Run the script** (background for large sites such as Press).
4. **Read the report** and sanity-check it (below), then summarise: the counts table, flagged accounts, and log coverage limits. Do not paste the file.

## What the review does

- **Active staff** = Employee `status = Active` or Intern `status = Internship Ongoing`. They are excluded and never listed.
- **Ex-employees** = Employee status Inactive, Suspended or Left, with `relieving_date`. **Ex-interns** = Intern status `Internship Completed`, with `end_date`. Interns with status Not Started are neither.
- Matching to site users is by email (`user_id`, company and personal email for employees; `user_id` for interns).
- **Summary:** counts of *enabled* System User and Website User accounts (and people) that belong to ex-employees and ex-interns, plus a list of those accounts capped at 50 per user type (most recent leavers first; the heading says when it is truncated). It does not list or count other users.
- **Activity review:** for ex-employees and ex-interns who left in the past year, finds their accounts (enabled or disabled) and counts activity after the relieving or end date: successful logins (`Activity Log`), downloads/exports/prints (`Access Log`), doctypes changed (`Version`), doctypes deleted (`Deleted Document`), doctypes viewed (`View Log`, if tracked), plus `last_login` and `last_active`.

## Sanity checks before reporting

- Compare the report's log coverage dates with the review window. `Activity Log` and `Access Log` often start only weeks ago. Say "no activity recorded since <date>", never "no activity".
- A zero must come from a working query. If everything is 0, test one known active user against the same doctype first.
- Website Users on Press are usually customers. A former employee's personal-Gmail account there is probably their own customer account, not staff access. Say so and do not call it a breach.
- `last_active` after the account was disabled is not proof of use. See [REFERENCE.md](REFERENCE.md).

## Rules

- Strictly read-only. Never disable users, edit records or run `frappectl auth`/mutating commands. List recommended actions instead.
- Do not print secrets from `Version` data (`request_key`, `otp`, passwords, API keys).
- Report faithfully: a failed or empty query is a limit to state, not a clean result.
- If the user asks for a list of current staff or other accounts, say this skill deliberately counts only ex-employee and ex-intern accounts.

For query details, field names, gotchas and extra manual checks, see [REFERENCE.md](REFERENCE.md).
