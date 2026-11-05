# site-access-review

A Claude Code skill that reviews who still has access to a Frappe site after they have left.

Given a site name, it:

1. Reads Employee and Intern records from https://frappe.io, which is the source of truth.
2. Counts the enabled System User and Website User accounts on the site that belong to ex-employees and ex-interns, and lists them (up to 50 per user type).
3. For people who left in the past year, checks their activity after their relieving or end date: logins, downloads and exports, doctypes changed, doctypes deleted, and doctypes viewed where the site tracks views.
4. Writes a markdown report, `access-review-<site>.md`, in the current directory.

The review is read-only. It never disables users or changes any data.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3
- [`frappectl`](https://github.com/frappe/frappectl) installed and on your `PATH` (check with `frappectl --version`)
- `frappectl` profiles for:
  - **https://frappe.io**, which is required because the Employee and Intern records come from there;
  - the **site you want to review**, for example support, press, crm or insights.

Check your profiles with:

```bash
frappectl auth list
```

## Install

### Option 1: with the skills CLI (needs Node.js)

```bash
npx skills add shadrak98/site-access-review -g -y
```

`-g` installs it for your user (available in every project) and `-y` skips the confirmation prompts. While the repo is private, the machine needs GitHub access to it (for example `gh auth login`).

To update later: `npx skills update`.

### Option 2: clone it yourself

```bash
git clone git@github.com:shadrak98/site-access-review.git ~/.claude/skills/site-access-review
```

### After installing

Start a new Claude Code session so it picks up the skill. The skill should then appear in the list of available skills.

The repo contains `SKILL.md`, `REFERENCE.md` and `scripts/review.py`. `SKILL.md` links to the other two, so all three must be present.

## Log in to the sites

If a profile is missing or its login has expired, log in from your own terminal (in Claude Code, prefix the command with `!`):

```bash
frappectl auth login https://frappe.io
frappectl auth login https://support.frappe.io   # or the site you want to review
```

Logging in again can create a new profile name, so run `frappectl auth list` afterwards and use the name it shows.

## Use

### Through Claude Code

Ask in plain words, naming the site:

> Run an access review for support
>
> Check which ex-employees still have access on press and whether they did anything after leaving

Claude finds the matching `frappectl` profile, checks the frappe.io profile works, runs the review and summarises the report.

### Directly from the command line

```bash
python3 ~/.claude/skills/site-access-review/scripts/review.py --site <profile>
```

| Option | Meaning |
|---|---|
| `--site` | **Required.** The `frappectl` profile of the site to review. Profile names are case-sensitive. |
| `--hr-site` | The profile for https://frappe.io. Optional. If left out, the script picks the first profile whose site is https://frappe.io. Use it only when you have more than one such profile. |
| `--days` | How far back to look for people who left. Default 365. |
| `--out` | Report file name. Default `access-review-<site>.md`. |

Run it from the folder where you want the report to be written. A large site such as Press can take several minutes.

## What the report contains

1. A table of enabled System User and Website User accounts belonging to ex-employees and ex-interns, with counts of accounts and people.
2. The list of those accounts, capped at 50 per user type, most recent leavers first.
3. An activity table for everyone who left in the past year: `last_login`, `last_active`, and counts of logins, downloads, changes and deletions after they left, with a flag column.
4. A detail section for each flagged account, grouped by doctype.
5. Log coverage dates and limits.

## Who counts as who

- **Active:** Employee status Active, or Intern status Internship Ongoing. Active people are not listed.
- **Ex-employee:** Employee status Inactive, Suspended or Left, dated by `relieving_date`.
- **Ex-intern:** Intern status Internship Completed, dated by `end_date`.
- Accounts are matched to people by email. If someone has more than one record, for example intern and then employee, activity is measured from their latest end date.

## Limits to keep in mind

- `Activity Log` and `Access Log` often go back only a few weeks, so "no activity" means none recorded since the date shown in the report.
- Frappe does not log plain reads of documents. "Accessed" means changed, downloaded or exported, deleted, or viewed where the site tracks views.
- `last_login` and `last_active` hold only the latest value.
- Use of API keys or OAuth tokens may not appear as logins.
- On Press, an ex-employee's personal-email Website User account is usually their own customer account, not staff access.
- Matching is by email only.

## Troubleshooting

| Message | What to do |
|---|---|
| `No frappectl profile named '<site>'` | Profile names are case-sensitive. The message lists the available ones. |
| `No frappectl profile for https://frappe.io` | Run `frappectl auth login https://frappe.io`. |
| `cannot read Employee records` or an OAuth refresh error | The login expired. Log in again, then run `frappectl auth list` to check the profile name. |
