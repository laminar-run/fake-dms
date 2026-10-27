# DealerDesk 98 - Fake Dealership Management System (DMS)

A fully functional, deliberately old-school **Windows 98-style desktop** Dealership Management
System built as an RPA testing target - the dealership-domain sibling of `fake-emr` (MedChart Pro 98).
Tkinter UI, single SQLite database, idempotent seed data, and a DB-driven "chaos engine" that injects
realistic enterprise-app friction (fake freezes, error dialogs, session timeouts, BSOD, etc.).

## Run

```bash
pip install -r requirements.txt          # pywin32, Pillow (desktop deps)
python main.py                           # launches the Win98 desktop app
python create_shortcut.py                # (Windows) puts "DealerDesk 98.lnk" on the Desktop
```

The database `dms.db` is created and seeded automatically on first launch (idempotent - safe to re-run).

## Logins

| Username | Password | Role |
|----------|----------|------|
| `admin`    | `admin`    | admin |
| `jmiller`  | `password` | salesperson |
| `rdavis`   | `password` | advisor |

## Modules (left navigation)

- **Home** - retro dashboard (clock, marquee, module status, quick stats)
- **Customers** - customer master; detail window has tabs: Profile / Vehicles / Repair Orders / Deals / Appointments
- **Inventory** - vehicles on the lot (In Stock / Sold / Customer-Owned)
- **Deals** - sales transactions (primary sales flow)
- **Repair Orders** - service write-ups using the "3 C's": Concern / Cause / Correction (+ Recommendations) - primary service flow
- **Appointments** - service & sales appointments
- **Reports** - canned dealership reports
- **Settings** - chaos engine configuration (off by default)

## Domain mapping (vs. fake-emr / MedChart)

| MedChart (EMR) | DealerDesk (DMS) |
|----------------|------------------|
| Patient | Customer |
| MRN | Customer # |
| Encounter (SOAP note) | Repair Order (3 C's) |
| Provider | Service Advisor / Salesperson |
| Medications / Diagnoses | Vehicles / Deals |
| Appointment | Appointment (Service/Sales) |

## Chaos engine

Off by default (`chaos_settings.master_enabled = 0`). Toggle scenarios in the **Settings** panel
or with the "Fire Now" buttons. Scenario keys match `chaos/engine.py` `SCENARIO_MAP`
(the `wrong_patient` key is reused for the wrong-customer warning).

## Stable selectors for RPA

Every interactive widget has a stable Tk `name=` (queryable via uiautomation/pywinauto by AutomationId/Name).
See `config.json -> use_cases` for full step-by-step flows. Highlights:

- Login: `username`, `password`, `btn_login`
- Nav: `btn_nav_home`, `btn_nav_customers`, `btn_nav_inventory`, `btn_nav_deals`, `btn_nav_repair_orders`, `btn_nav_appointments`, `btn_nav_reports`, `btn_nav_settings`
- Customers: `customer_search`, `btn_search_customers`, `customer_tree`, `btn_open_customer`, `btn_add_customer`
- Repair Order form: `btn_new_ro`, `ro_customer`/`btn_ro_lookup_customer`, `ro_vehicle`/`btn_ro_lookup_vehicle`, `ro_date`, `ro_type`, `ro_advisor`, `ro_status`, `ro_mileage`, `ro_concern`, `ro_cause`, `ro_correction`, `ro_recommendations`, `btn_save_ro`
- Deal form: `btn_new_deal`, `btn_deal_lookup_customer`, `btn_deal_lookup_vehicle`, `deal_date`, `deal_salesperson`, `deal_type`, `deal_sale_price`, `deal_status`, `btn_save_deal`
- Appointment form: `btn_new_appt`, `btn_appt_lookup_customer`, `appt_datetime`, `appt_dept`, `appt_advisor`, `appt_reason`, `appt_status`, `btn_save_appt`
- Inventory: `inventory_search`, `inventory_status_filter`, `btn_search_inventory`, `inventory_tree`

## Workflow action installation

Install the action for each Windows user that runs DealerDesk.
Run these commands from the DealerDesk directory in that user's session.

```powershell
pip install -r requirements.txt
python -m action_control.install --instance installation-a --version (git rev-parse HEAD)
python main.py
```

The installer atomically writes `%ProgramData%\Minicor\actions\registrations\<user>\dealerdesk.json`.
The user needs write access to that directory and MDS needs read access.
Remove the registration file to uninstall the action, then restart DealerDesk.
MDS advertises installed definitions on its next heartbeat, whether or not DealerDesk is running.
DealerDesk polls its registered file inbox on the Tk thread every 100 ms; no server is started.
A stopped app does not consume requests, and expired requests are discarded on restart.
The inbox is `%ProgramData%\Minicor\actions\inboxes\<user>\<identity>`, where identity is the SHA-256 hex digest of UTF-8 `appId + NUL + instanceId`.
The installer creates it and records its absolute path as `inbox`; both MDS and DealerDesk need read/write access.
Local processes with that filesystem access can submit requests.
The action ID is `dealerdesk.critical-error`, version 1, with empty `{}` parameters.
It acknowledges completion after the critical error dialog has been created on the Tk thread.
A reused request ID returns the saved outcome or `unknown` after interruption.
Receipts are appended to `%LOCALAPPDATA%\DealerDesk\actions\<instance>.executed-actions.jsonl` as plain-text JSON lines.
The app flushes a `started` entry before executing and an `outcome` entry afterward, under an exclusive file lock.
After a restart, a request with only `started` returns `unknown`; completed requests return their saved outcome.
A malformed or incomplete log prevents further effects and returns `unknown` until the log is repaired.
The log is retained without automatic rotation; deleting it removes the app's duplicate protection.

### File protocol

A sender atomically renames `<sha256(requestId)>.request.tmp` to `<sha256(requestId)>.request.json`.
Its UTF-8 JSON body is `{"request": <action request>, "createdAt": <Unix seconds>, "expiresAt": <Unix seconds>}`.
The request and result interfaces are unchanged; timestamps belong to the transport envelope.
The app orders each pending snapshot by `createdAt`, then by request ID for equal timestamps.
This orders requests already present, not requests that arrive after a snapshot.
MDS sets a 15-second deadline and removes stale results before publishing.
The receiver claims a request by creating a hard link named `<hash>.processing.json` without replacing an existing claim, then removes the request name.
Both files are on the same local NTFS volume.
After creating the effect, it atomically publishes `<hash>.result.json` containing the action result.
Requests larger than 64 KiB, malformed requests, and requests past their deadline are discarded.
MDS waits up to 15 seconds, validates the matching request ID, and removes its request and result files.
A timeout returns `unknown`; a claimed action may already have happened.
The receiver removes its processing file after handling and stale files after 60 seconds.
An interrupted processing file is never replayed; the text log prevents repeating acknowledged effects while retained.
