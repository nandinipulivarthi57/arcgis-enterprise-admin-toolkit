# ArcGIS Enterprise Admin Toolkit

Self-directed practice project: two automation scripts covering core
ArcGIS Enterprise administration tasks — Portal user governance /
license reporting, and patch discovery.

## Contents

### `portal_user_governance.py`
Uses the **ArcGIS API for Python** (`arcgis.gis.GIS`) to connect to an
ArcGIS Enterprise Portal (or ArcGIS Online org) as an administrator and
produce three CSV reports:

- **`user_license_report.csv`** — every user's username, full name,
  email, user type / license type, role, and last login date.
- **`orphan_inactive_users.csv`** — accounts that have never logged in,
  or have been inactive longer than a configurable threshold —
  candidates for license reclamation.
- **`external_user_compliance.csv`** — accounts whose email domain
  isn't on the organization's approved internal domain list.

Reference: [Esri Support — Determine the last login in ArcGIS Enterprise
portal and ArcGIS Online using ArcGIS API for
Python](https://support.esri.com/en-us/knowledge-base/how-to-determine-the-last-login-in-arcgis-enterprise-po-000022604)

### `Check-ArcGISPatches.ps1`
PowerShell script that authenticates against ArcGIS Enterprise and calls
the **ArcGIS Enterprise Administrator REST API**'s upgrade operations to
report:

- Currently **installed** patches/releases (`system/upgrades/installed`)
- Patches/releases **available but not yet installed**
  (`system/upgrades/available`) — i.e., patch discovery

Reference: [Esri REST API docs — Installed](https://developers.arcgis.com/rest/enterprise-administration/enterprise/check-installed-updates/) /
[Available](https://developers.arcgis.com/rest/enterprise-administration/enterprise/check-available-updates/)

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # fill in your Portal URL/credentials
python portal_user_governance.py
```

```powershell
./Check-ArcGISPatches.ps1 -PortalUrl "https://gis.example.com/portal" `
    -AdminUrl "https://gis.example.com/portal/portaladmin" `
    -Username "admin_user" -Password "***" -OutputPath "./reports"
```

## Notes

This is a learning/practice project built to develop hands-on ArcGIS
Enterprise administration skills (user governance, licensing, and patch
management) alongside existing ArcGIS development experience. Never
commit a real `.env` file or real credentials — `.env` is gitignored.
