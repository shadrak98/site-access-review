# Reference

## Where each kind of activity is recorded

| Question | DocType | Key fields | Notes |
|---|---|---|---|
| Logged in after exit? | `Activity Log` | `user`, `operation`, `status`, `ip_address`, `creation` | Use `operation = Login`, `status = Success`. Retention is set in `Log Settings` (often 90 days) and the oldest row can be much newer. |
| Downloaded or exported? | `Access Log` | `user`, `export_from`, `file_type`, `reference_document`, `method`, `report_name`, `filters`, `columns`, `creation` | `export_from = File` is a file or attachment download or inline view. Report/list exports have `method = Export` and a `report_name`. PDFs and prints appear as `file_type = PDF`. No record count is stored. |
| Changed data? | `Version` | `ref_doctype`, `docname`, `owner`, `data`, `creation` | `owner` is the user who made the change. Only for DocTypes with change tracking. |
| Deleted data? | `Deleted Document` | `deleted_doctype`, `deleted_name`, `owner`, `creation` | `owner` is the user who deleted. History is long (years). |
| Viewed documents? | `View Log` | `reference_doctype`, `reference_name`, `viewed_by` | Only DocTypes with `track_views`. May not exist on a site. |
| Last seen | `User` | `last_login`, `last_active`, `last_ip`, `enabled`, `user_type` | Latest value only. |

Plain reads of documents are not logged anywhere, so "accessed" can only mean the rows above.

## last_active

Set at login, then by `Session.update()` on authenticated requests at most every 10 minutes, and by `bench set-last-active-for-user`. It is written without changing `modified`, so there is no `Version` row. Disabling a user normally clears their sessions, so a `last_active` months after disabling is unexplained by normal use. Report it as unexplained, not as misuse. `last_login` (set when a session is created) is the more reliable signal.

## frappectl quirks

- `frappectl doc list` fails on `Activity Log` and `Access Log` ("Unsupported filters type"). Use `api method/frappe.client.get_list` with `-F fields=[...] -F filters=[...] -F limit_page_length=0`.
- `get_list` needs plain field names. `count(name) as n` is rejected, so group client-side.
- Some fields are rejected on some sites (for example `full_name` on Press gave a 500, and `role` on `Account Request` was not permitted). Retry with fewer fields.
- `doc list --all` returned only 200 of 511,681 website users on Press. For big user sets use `get_count`, `name in [...]` chunks of about 40 emails, and `name like %@domain`.
- Mutations need `--yes`; profiles here are read-only, so do not try.
- An expired OAuth profile says "Could not refresh the OAuth session". Re-login may create a new profile name.

## Interpreting results

- **Exports with reports** (for example "FC ticket info") are normal for support staff. Judge by who, how many, and whether the person had left.
- `Access Log` file rows are mostly inline image loads. Filter out `png/jpg/jpeg/gif` when looking for deliberate downloads.
- Version rows for `Product Trial Request` and `Site` created in seconds of each other are automated trial provisioning by a customer account, not staff edits.
- `Account Request` Version rows with `request_key`/`otp` changes are an email-code login. Their timestamp matches `last_login`.
- An enabled account of a Left employee is a finding even if there is no activity. Recommend disabling, but do not do it.

## Extra manual checks if a finding needs follow-up

- Other emails for the same person (for example a personal domain) with their own `Account Request` or `User`.
- The Press team that owns a flagged account, and whether anything changed on it after exit.
- Whether other disabled accounts also show late `last_active`, which would point to a system process.
- Web server or `API Request Log` (90-day retention) for API-key and OAuth use.

## Report layout the script writes

1. Counts of enabled System User and Website User accounts (and people) for ex-employees and ex-interns.
2. Activity table with one row per ex-employee or ex-intern account that left in the window, with a Flag column.
3. Detail section per flagged account, by doctype.
4. Log coverage and limits.

## HR fields used on https://frappe.io

- Employee: `status`, `employee_name`, `user_id`, `company_email`, `personal_email`, `relieving_date`.
- Intern: `status` (Not Started, Internship Ongoing, Internship Completed), `full_name`, `user_id`, `end_date`.
