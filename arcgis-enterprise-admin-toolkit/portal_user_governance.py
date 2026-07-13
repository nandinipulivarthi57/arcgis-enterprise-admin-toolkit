"""
Portal User Governance & License Reporting
-------------------------------------------
Uses the ArcGIS API for Python (arcgis.gis) to connect to an ArcGIS
Enterprise Portal (or ArcGIS Online organization) and produce:

  1. A full user/license report (username, full name, email, user type,
     license type, role, last login).
  2. An orphan/inactive user report (never logged in, or inactive for
     more than INACTIVE_DAYS days) - useful for license reclamation.
  3. An external user compliance report (accounts whose email domain is
     not in the organization's approved internal domain list).

Reference: Esri Support - "Determine the last login in ArcGIS Enterprise
portal and ArcGIS Online using ArcGIS API for Python"
https://support.esri.com/en-us/knowledge-base/how-to-determine-the-last-login-in-arcgis-enterprise-po-000022604

Requires a .env file (not committed to source control) with:
    PORTAL_URL=https://portal.example.com/portal
    PORTAL_USERNAME=admin_user
    PORTAL_PASSWORD=admin_password
    INACTIVE_DAYS=90
    APPROVED_EMAIL_DOMAINS=county.gov,devnetinc.com
"""

import csv
import os
from datetime import datetime, timedelta

from arcgis.gis import GIS
from dotenv import load_dotenv

load_dotenv()

PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USERNAME = os.getenv("PORTAL_USERNAME")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD")
INACTIVE_DAYS = int(os.getenv("INACTIVE_DAYS", "90"))
APPROVED_EMAIL_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("APPROVED_EMAIL_DOMAINS", "").split(",")
    if d.strip()
}

OUTPUT_DIR = os.getenv("OUTPUT_DIR", ".")


def connect():
    """Connect as an administrator so we can read every user's lastLogin
    and license/user-type fields (regular users can't see this for others)."""
    gis = GIS(PORTAL_URL, username=PORTAL_USERNAME, password=PORTAL_PASSWORD, verify_cert=False)
    print(f"Connected to {PORTAL_URL} as {gis.properties.user.username}")
    return gis


def last_login_date(user):
    """arcgis.gis.User.lastLogin is epoch milliseconds, or -1 if the user
    has never logged in."""
    if getattr(user, "lastLogin", -1) in (-1, None):
        return None
    return datetime.fromtimestamp(user.lastLogin / 1000)


def build_user_report(gis, max_users=2000):
    """Full license/user-type/last-login report for every member."""
    users = gis.users.search(query="", max_users=max_users)
    rows = []
    for u in users:
        rows.append({
            "username": u.username,
            "full_name": u.fullName,
            "email": u.email or "",
            "user_type": getattr(u, "userLicenseTypeId", "") or "",
            "role": getattr(u, "role", "") or "",
            "last_login": last_login_date(u),
            "disabled": getattr(u, "disabled", False),
        })
    return rows


def flag_orphan_users(rows, inactive_days=INACTIVE_DAYS):
    """Users who have never logged in, or haven't logged in within the
    inactivity window - candidates for license reclamation / removal."""
    cutoff = datetime.now() - timedelta(days=inactive_days)
    orphans = []
    for r in rows:
        if r["last_login"] is None:
            orphans.append({**r, "reason": "never logged in"})
        elif r["last_login"] < cutoff:
            orphans.append({**r, "reason": f"inactive > {inactive_days} days"})
    return orphans


def flag_external_users(rows, approved_domains=APPROVED_EMAIL_DOMAINS):
    """Accounts whose email domain isn't on the approved internal list -
    used for external user compliance reporting."""
    if not approved_domains:
        return []
    flagged = []
    for r in rows:
        email = r["email"]
        if not email or "@" not in email:
            flagged.append({**r, "reason": "no email on file"})
            continue
        domain = email.split("@", 1)[1].lower()
        if domain not in approved_domains:
            flagged.append({**r, "reason": f"external domain: {domain}"})
    return flagged


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} row(s) to {path}")


def run():
    gis = connect()
    rows = build_user_report(gis)

    write_csv(
        os.path.join(OUTPUT_DIR, "user_license_report.csv"),
        rows,
        ["username", "full_name", "email", "user_type", "role", "last_login", "disabled"],
    )

    orphans = flag_orphan_users(rows)
    write_csv(
        os.path.join(OUTPUT_DIR, "orphan_inactive_users.csv"),
        orphans,
        ["username", "full_name", "email", "user_type", "role", "last_login", "disabled", "reason"],
    )

    external = flag_external_users(rows)
    write_csv(
        os.path.join(OUTPUT_DIR, "external_user_compliance.csv"),
        external,
        ["username", "full_name", "email", "user_type", "role", "last_login", "disabled", "reason"],
    )

    print(f"Total users: {len(rows)} | Orphan/inactive: {len(orphans)} | External/flagged: {len(external)}")


if __name__ == "__main__":
    run()
