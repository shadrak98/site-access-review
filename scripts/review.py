#!/usr/bin/env python3
"""Access review of a Frappe site against HR data on https://frappe.io (read-only).

usage: review.py --site <frappectl profile> [--hr-site <profile for https://frappe.io>]
                 [--days 365] [--out access-review-<site>.md]
"""
import argparse, collections, datetime, json, subprocess, sys

HR_URL = "https://frappe.io"
LIST_CAP = 50  # max users listed per user type


def run(site, *args):
    return subprocess.run(["frappectl", "-s", site, *args], capture_output=True, text=True)


def fc(site, *args):
    r = run(site, *args)
    try:
        return json.loads(r.stdout)
    except Exception:
        raise RuntimeError(f"frappectl -s {site} {' '.join(args[:3])} failed: {(r.stderr or r.stdout)[:300]}")


def get_list(site, doctype, fields, filters=None, order="creation asc", limit=0):
    d = fc(site, "api", "method/frappe.client.get_list", "-F", f"doctype={doctype}",
           "-F", "fields=" + json.dumps(fields), "-F", "filters=" + json.dumps(filters or []),
           "-F", f"limit_page_length={limit}", "-F", "order_by=" + order)
    if isinstance(d, dict):
        d = d.get("message", d)
    return d if isinstance(d, list) else []


def safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception:
        return None


def preflight(site, hr_site):
    """Return the profile name for https://frappe.io, or exit with instructions."""
    r = subprocess.run(["frappectl", "auth", "list"], capture_output=True, text=True)
    try:
        profiles = json.loads(r.stdout)
    except Exception:
        sys.exit("Could not read `frappectl auth list`: " + (r.stderr or r.stdout)[:200])
    names = {p["profile"]: p["site"].rstrip("/") for p in profiles}
    if site not in names:
        sys.exit(f"No frappectl profile named '{site}'. Profiles: {', '.join(names)}")
    if hr_site:
        hr = hr_site
        if names.get(hr) != HR_URL:
            sys.exit(f"Profile '{hr}' is not {HR_URL}. Employee and Intern records must come from {HR_URL}.")
    else:
        match = [n for n, u in names.items() if u == HR_URL]
        if not match:
            sys.exit(f"No frappectl profile for {HR_URL}, which is the source of truth for Employee and Intern records.\n"
                     f"Ask the user to run: ! frappectl auth login {HR_URL}")
        hr = match[0]
    t = run(hr, "api", "method/frappe.client.get_count", "-F", "doctype=Employee")
    if not t.stdout.strip().isdigit():
        sys.exit(f"Profile '{hr}' ({HR_URL}) cannot read Employee records: {(t.stderr or t.stdout)[:200]}\n"
                 f"Its login may have expired. Ask the user to run: ! frappectl auth login {HR_URL}")
    return hr


def chunks(xs, n=40):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def top(counter, n=8):
    return ", ".join(f"{k} ({v})" for k, v in counter.most_common(n)) or "-"


def clean(*xs):
    return sorted({x.strip().lower() for x in xs if x and x.strip()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="frappectl profile of the site to review")
    ap.add_argument("--hr-site", help="profile for https://frappe.io (auto-detected if omitted)")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--out")
    a = ap.parse_args()
    hr = preflight(a.site, a.hr_site)
    out = a.out or f"access-review-{a.site}.md".replace("/", "_")
    today = datetime.date.today()
    since = (today - datetime.timedelta(days=a.days)).isoformat()

    # 1. HR source of truth
    emp = fc(hr, "doc", "list", "Employee", "--all", "--json", "--fields",
             "name,employee_name,status,user_id,company_email,personal_email,relieving_date")
    interns = fc(hr, "doc", "list", "Intern", "--all", "--json", "--fields", "name,full_name,status,user_id,end_date")
    active, people = set(), []
    for e in emp:
        em = clean(e.get("user_id"), e.get("company_email"), e.get("personal_email"))
        if e["status"] == "Active":
            active.update(em)
        else:  # Inactive, Suspended, Left
            people.append(dict(kind="Employee", name=(e["employee_name"] or e["name"]).strip(), ref=e["name"],
                               status=e["status"], end=e.get("relieving_date") or "", emails=em))
    for i in interns:
        em = clean(i.get("user_id"))
        if i["status"] == "Internship Ongoing":
            active.update(em)
        elif i["status"] == "Internship Completed":
            people.append(dict(kind="Intern", name=(i.get("full_name") or i["name"]).strip(), ref=i["name"],
                               status=i["status"], end=i.get("end_date") or "", emails=em))
    for p in people:  # someone who is active under another record is not an ex-user
        p["emails"] = [x for x in p["emails"] if x not in active]
    people = [p for p in people if p["emails"]]

    # 2. Find their accounts on the site (enabled or not)
    owner = {x: p for p in sorted(people, key=lambda q: q["end"]) for x in p["emails"]}  # latest end date wins
    accounts = {}
    for c in chunks(sorted(owner)):
        for u in get_list(a.site, "User", ["name", "enabled", "user_type", "last_login", "last_active"], [["name", "in", c]]):
            accounts[u["name"].lower()] = u

    summary, listing = [], {}
    for utype in ("System User", "Website User"):
        enabled = sorted(((x, u) for x, u in accounts.items() if u["user_type"] == utype and u["enabled"]),
                         key=lambda t: owner[t[0]]["end"], reverse=True)
        listing[utype] = [(x, owner[x]["kind"], owner[x]["name"], owner[x]["status"], owner[x]["end"],
                           (u["last_login"] or "")[:10], (u["last_active"] or "")[:10]) for x, u in enabled]
        row = [utype]
        for kind in ("Employee", "Intern"):
            en = [x for x, u in accounts.items() if u["user_type"] == utype and u["enabled"] and owner[x]["kind"] == kind]
            row.append(f"{len(en)} accounts ({len({owner[x]['ref'] for x in en})} people)")
        summary.append(row)

    # 3. Activity after end date for ex-people who left within the window
    cover = {dt: (safe(get_list, a.site, dt, ["creation"], None, "creation asc", 1) or [{}])[:1] for dt in ("Activity Log", "Access Log")}
    review = sorted((p for p in people if p["end"] >= since), key=lambda p: p["end"], reverse=True)
    rows, details = [], []
    for p in review:
        after = p["end"] + " 23:59:59"
        for em in p["emails"]:
            u = accounts.get(em)
            if not u or owner[em] is not p:  # same email under an earlier record (e.g. intern then employee)
                continue
            ll, la = (u["last_login"] or "")[:10], (u["last_active"] or "")[:10]
            logins = get_list(a.site, "Activity Log", ["creation"],
                              [["user", "=", em], ["creation", ">", after], ["operation", "=", "Login"], ["status", "=", "Success"]])
            acc = get_list(a.site, "Access Log", ["export_from", "file_type", "method", "report_name"], [["user", "=", em], ["creation", ">", after]])
            ver = get_list(a.site, "Version", ["ref_doctype"], [["owner", "=", em], ["creation", ">", after]])
            dele = get_list(a.site, "Deleted Document", ["deleted_doctype"], [["owner", "=", em], ["creation", ">", after]])
            views = safe(get_list, a.site, "View Log", ["reference_doctype"], [["viewed_by", "=", em], ["creation", ">", after]]) or []
            flag = bool(logins or acc or ver or dele or views or ll > p["end"] or la > p["end"])
            rows.append((p["end"], p["kind"], p["name"], em, "enabled" if u["enabled"] else "disabled", u["user_type"], ll, la,
                         len(logins), len(acc), len(ver), len(dele), "YES" if flag else "no"))
            if flag:
                downloads = collections.Counter((x["export_from"] or x["report_name"] or "?") + "/" + (x["file_type"] or x["method"] or "?") for x in acc)
                details.append(f"#### {p['name']} ({p['kind']}) - {em}, ended {p['end']}\n"
                               f"- Successful logins after end (Activity Log): {len(logins)}\n"
                               f"- Downloads/exports (Access Log): {top(downloads)}\n"
                               f"- Doctypes changed (Version): {top(collections.Counter(x['ref_doctype'] for x in ver))}\n"
                               f"- Doctypes deleted (Deleted Document): {top(collections.Counter(x['deleted_doctype'] for x in dele))}\n"
                               f"- Doctypes viewed (View Log): {top(collections.Counter(x['reference_doctype'] for x in views))}\n"
                               f"- last_login {ll or '-'}, last_active {la or '-'}")

    # 4. Report (counts only for enabled accounts; no listing of current staff)
    n_flag = sum(1 for r in rows if r[-1] == "YES")
    L = [f"# Access review: {a.site}",
         f"\nGenerated {today}. HR source: {HR_URL} (profile `{hr}`). Activity window: people who left on or after {since}.\n",
         "## Enabled accounts belonging to ex-employees and ex-interns\n",
         md_table(["User type", "Ex-employees (Inactive, Suspended, Left)", "Ex-interns (Internship Completed)"], summary),
         "\nCounts cover every ex-employee and ex-intern in HR, not only the past year. Matching is by email. "
         "Active employees and ongoing interns are excluded and not listed.\n",
         *[line for ut in ("System User", "Website User") for line in (
             f"### Enabled {ut} accounts of ex-employees and ex-interns ({len(listing[ut])}"
             + (f", showing the {LIST_CAP} most recent leavers)\n" if len(listing[ut]) > LIST_CAP else ")\n"),
             md_table(["Account", "Type", "Person", "HR status", "Left on", "last_login", "last_active"], listing[ut][:LIST_CAP])
             if listing[ut] else "None.", "")],
         f"## Activity after leaving ({len(review)} people left since {since}; {len(rows)} accounts found; {n_flag} flagged)\n"]
    L.append(md_table(["Ended", "Type", "Person", "Account", "State", "User type", "last_login", "last_active",
                       "Logins after", "Downloads after", "Changes after", "Deletions after", "Flag"], rows)
             if rows else "None of them has an account on this site.")
    if details:
        L.append("\n### Detail for flagged accounts\n")
        L += details
    L.append("\n## Log coverage and limits\n")
    for dt, v in cover.items():
        L.append(f"- {dt} oldest row: {(v[0].get('creation') or 'none')[:10] if v else 'unreadable'}. Earlier activity is invisible.")
    L += ["- last_login/last_active keep only the latest value; last_active can update without a login.",
          "- Reads are not logged, so 'accessed' means changed (Version), downloaded/exported/printed (Access Log), deleted (Deleted Document) and, if enabled, viewed (View Log).",
          "- API-key/OAuth use may not appear as logins. Interns with status Not Started are neither active nor ex. Matching is by email only."]
    open(out, "w").write("\n".join(L) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(str(e))
