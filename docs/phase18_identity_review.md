# Phase 18 unresolved identity review

There are **572 open xgEdge identity-review rows** and **0 verified xgEdge
provider-ID mappings** in the staged PostgreSQL data. The persistent
`historical_data/player_identity_crosswalk.json` file was absent. These rows
mean that a stable external ID was not available in the staged evidence;
they do **not** mean a name-based comparison found 572 failures. No two
players were merged by name. Official TFF IDs 1:1 map to the 572 normalized
players and remain the primary keys.

The third-party preseason workbook contributed 395 lower-confidence
position observations through the existing corroborated recovery output.
Its workbook IDs were not used as TFF or xgEdge identity keys. If a verified
crosswalk becomes available, import it as a new version with the source URL,
review evidence and validity interval; do not revise these rows silently.

Read-only review query, after loading `$dbUser` and `$dbName` as documented
in `phase17_postgres_setup.md`:

```powershell
docker compose exec -T db psql -U $dbUser -d $dbName -c 'SELECT r.player_id, p.name, r.provider, r.reason, r.status FROM identity_reviews r JOIN players p ON p.id=r.player_id WHERE r.status=''open'' ORDER BY r.player_id LIMIT 30;'
```

The full review set remains queryable in PostgreSQL. No unresolved external
match has been promoted to a verified identity.
