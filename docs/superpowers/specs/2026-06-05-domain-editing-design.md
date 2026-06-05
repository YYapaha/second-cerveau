# Domain Editing — Design Spec
*2026-06-05*

## Goal

Allow renaming domain names and changing their dot color directly from the Electron UI, without restarting the server.

## Approach

SQLite table `domains` as single source of truth. Frontend fetches domains dynamically at startup. Edits call new PATCH endpoint which cascades to notes.

---

## Database

New table in `brain.db`, created by `initialiser_db()` in `brain_agent.py`:

```sql
CREATE TABLE IF NOT EXISTS domains (
  name     TEXT PRIMARY KEY,
  color    TEXT NOT NULL,   -- hex string e.g. '#a8d8a8'
  position INTEGER NOT NULL
);
```

Seed on creation with the 7 current hardcoded domains, colors converted from oklch to hex approximations:

| name                | color     | position |
|---------------------|-----------|----------|
| Travail             | #d4b96a   | 0        |
| Apprentissage       | #7aa0d4   | 1        |
| Projets perso       | #d47a6a   | 2        |
| Jeux vidéos         | #c87ad4   | 3        |
| Plantes             | #7ac88a   | 4        |
| Organisation TDAH   | #7ac8c8   | 5        |
| À trier             | #c8b87a   | 6        |

Migration is additive only: if the table already exists, no-op.

---

## API

### `GET /domains`
Returns domains sorted by `position`.

Response `200`:
```json
[
  {"name": "Travail", "color": "#d4b96a", "position": 0},
  ...
]
```

### `PATCH /domains/{name}`
Updates name and/or color. At least one field required.

Request body (both fields optional, but at least one must be present):
```json
{"name": "Nouveau nom", "color": "#ff0000"}
```

Rules:
- `name` of "À trier" is non-renameable → 400 `{"error": "cannot_rename_default_domain"}`
- Empty new name → 422
- New name already exists → 409
- Unknown `{name}` → 404
- On rename: `UPDATE notes SET domaine = ? WHERE domaine = ?` in same transaction
- On color: `UPDATE domains SET color = ? WHERE name = ?`

Response `200`: updated domain object.

---

## Frontend (`renderer.js`)

### Startup

Replace the hardcoded `const DOMAINS = {...}` with a dynamic fetch:

```js
async function loadDomains() {
  const res = await fetch(`${API}/domains`);
  return res.json(); // [{name, color, position}]
}
```

Fallback to current hardcoded object if fetch fails (server unavailable).

### Domain pill rendering

Pills built from fetched data. Color dot uses inline style:
```html
<span class="ddot" style="background: #d4b96a; box-shadow: 0 0 6px #d4b96a"></span>
```

### Inline rename

- Double-click on domain label → replace text node with `<input>` pre-filled with current name
- `Enter` or `blur` → `PATCH /domains/{name}` with `{name: newValue}`
- `Escape` → revert to original text, no API call
- "À trier" pill: label has `data-locked="true"`, double-click is no-op

### Color picker

- Click on dot → `<input type="color">` popover appears near the dot (absolute positioned)
- `change` event → `PATCH /domains/{name}` with `{color: hexValue}`, dot updates inline immediately
- Click outside → popover closes

### Feedback

- During save: dot opacity pulses 0.5 → 1 via anime.js (same pattern as existing animations)
- On API error: revert value + flash `border-color: red` on the pill for 800ms

---

## Tests

### New tests (`test_brain_server.py`)

- `GET /domains` → 200, returns 7 domains sorted by position
- `PATCH /domains/Travail` with `{name: "Boulot"}` → 200, notes updated in cascade
- `PATCH /domains/Travail` with `{color: "#ff0000"}` → 200, color updated
- `PATCH /domains/Travail` with both name + color → 200
- `PATCH /domains/À trier` with `{name: "Autre"}` → 400
- `PATCH /domains/Travail` with `{name: ""}` → 422
- `PATCH /domains/Travail` with `{name: "Apprentissage"}` → 409 (duplicate)
- `PATCH /domains/Inexistant` → 404

### Migration test (`test_brain_agent.py`)

- `initialiser_db()` on fresh DB → `domains` table exists, 7 rows seeded
- Calling `initialiser_db()` twice → no duplicate rows

### Updated existing tests

- Any test that references hardcoded `DOMAINS` list → updated to fetch from `GET /domains` or use the new seeded data

---

## Out of scope

- Adding new domains (only rename/recolor existing ones)
- Deleting domains
- Reordering domains
- "À trier" color is editable, only its name is locked
