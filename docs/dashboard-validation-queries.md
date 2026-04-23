# Dashboard Validation Queries

SQL queries to validate dashboard data against the database. These correspond to the metrics computed in `backend/features/functional/services/dashboard_service.py`.

> **Note:** For a **non-superuser**, add `AND owner_id = <USER_ID>` to every subquery on the `projects` table.

---

## 1. Accessible Project IDs

**Superuser:**
```sql
SELECT id FROM projects WHERE is_active = true;
```

**Non-superuser:**
```sql
SELECT id FROM projects WHERE is_active = true AND owner_id = <USER_ID>;
```

## 2. Project Count

```sql
SELECT COUNT(*) FROM projects WHERE is_active = true;
```

## 3. Total Test Cases

```sql
SELECT COUNT(id) FROM test_cases
WHERE project_id IN (SELECT id FROM projects WHERE is_active = true);
```

## 4. Run Status Aggregates

Per-status breakdown:
```sql
SELECT status, COUNT(id) FROM test_runs
WHERE project_id IN (SELECT id FROM projects WHERE is_active = true)
GROUP BY status;
```

Dashboard card values:
```sql
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status = 'passed') AS passed,
  COUNT(*) FILTER (WHERE status IN ('failed', 'error')) AS failed,
  COUNT(*) FILTER (WHERE status = 'running') AS running,
  COUNT(*) FILTER (WHERE status = 'pending') AS pending,
  COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
  CASE
    WHEN COUNT(*) > 0
    THEN ROUND(COUNT(*) FILTER (WHERE status = 'passed') * 100.0 / COUNT(*))
    ELSE 0
  END AS avg_pass_rate
FROM test_runs
WHERE project_id IN (SELECT id FROM projects WHERE is_active = true);
```

## 5. Recent Runs (last 8)

```sql
SELECT tr.id, tr.project_id, p.name AS project_name,
       tr.name, tr.description, tr.status, tr.created_at
FROM test_runs tr
JOIN projects p ON tr.project_id = p.id
WHERE tr.project_id IN (SELECT id FROM projects WHERE is_active = true)
ORDER BY tr.created_at DESC
LIMIT 8;
```

## 6. Recent Projects (last 5 updated)

```sql
SELECT id, name, description, updated_at
FROM projects
WHERE is_active = true
ORDER BY updated_at DESC
LIMIT 5;
```

## 7. Activity by Day (last 7 days)

```sql
SELECT
  DATE(created_at AT TIME ZONE 'UTC') AS day,
  COUNT(*) FILTER (WHERE status = 'passed') AS passed,
  COUNT(*) FILTER (WHERE status IN ('failed', 'error')) AS failed,
  COUNT(*) FILTER (WHERE status NOT IN ('passed', 'failed', 'error')) AS other
FROM test_runs
WHERE project_id IN (SELECT id FROM projects WHERE is_active = true)
  AND created_at >= (CURRENT_DATE - INTERVAL '6 days')
GROUP BY DATE(created_at AT TIME ZONE 'UTC')
ORDER BY day;
```
