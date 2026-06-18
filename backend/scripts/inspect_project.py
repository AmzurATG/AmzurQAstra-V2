"""One-off script to inspect project data in the database."""
import json
import sys
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://qastra:qastra123@localhost:5432/qastra"
PROJECT_FILTER = sys.argv[1] if len(sys.argv) > 1 else "f2mx-2"
PROJECT_ID = int(sys.argv[2]) if len(sys.argv) > 2 else None


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        if PROJECT_ID:
            projects = conn.execute(
                text(
                    """
                    SELECT id, name, description, app_url, is_active, created_at,
                           jira_project_key, azure_devops_project
                    FROM projects WHERE id = :pid
                    """
                ),
                {"pid": PROJECT_ID},
            ).mappings().all()
        else:
            projects = conn.execute(
                text(
                    """
                    SELECT id, name, description, app_url, is_active, created_at,
                           jira_project_key, azure_devops_project
                    FROM projects
                    WHERE name ILIKE :pat OR app_url ILIKE :pat
                    ORDER BY id
                    """
                ),
                {"pat": f"%{PROJECT_FILTER}%"},
            ).mappings().all()

        print("=== PROJECTS (matched) ===")
        print(json.dumps([dict(r) for r in projects], default=str, indent=2))

        if not projects:
            print("No project found.")
            return

        # Prefer exact name match when multiple projects share the same app URL
        target = next(
            (p for p in projects if p["name"].lower() == PROJECT_FILTER.lower()),
            projects[-1],
        )
        pid = target["id"]
        print(f"\nUsing project_id={pid} ({target['name']})\n")

        reqs = conn.execute(
            text(
                """
                SELECT id, title, file_name, file_type, created_at
                FROM requirements
                WHERE project_id = :pid
                ORDER BY id
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("=== REQUIREMENTS ===")
        print(f"Count: {len(reqs)}")
        for r in reqs:
            print(dict(r))

        stories = conn.execute(
            text(
                """
                SELECT id, external_key, title, source, status, priority, item_type,
                       LEFT(COALESCE(acceptance_criteria, ''), 200) AS ac_preview,
                       integrity_check, created_at
                FROM user_stories
                WHERE project_id = :pid
                ORDER BY id
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("\n=== USER STORIES ===")
        print(f"Count: {len(stories)}")
        for s in stories:
            print(dict(s))

        tc_summary = conn.execute(
            text(
                """
                SELECT status, source, is_generated, scenario_type, COUNT(*) AS cnt
                FROM test_cases
                WHERE project_id = :pid
                GROUP BY status, source, is_generated, scenario_type
                ORDER BY cnt DESC
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("\n=== TEST CASES SUMMARY ===")
        for row in tc_summary:
            print(dict(row))

        tc_total = conn.execute(
            text("SELECT COUNT(*) FROM test_cases WHERE project_id = :pid"),
            {"pid": pid},
        ).scalar()
        print(f"Total test cases: {tc_total}")

        tcs = conn.execute(
            text(
                """
                SELECT tc.id, tc.case_number, tc.title, tc.status, tc.priority, tc.category,
                       tc.source, tc.is_generated, tc.scenario_type, tc.ac_ref,
                       tc.user_story_id, us.external_key AS story_key, us.title AS story_title,
                       (SELECT COUNT(*) FROM test_steps ts WHERE ts.test_case_id = tc.id) AS step_count
                FROM test_cases tc
                LEFT JOIN user_stories us ON us.id = tc.user_story_id
                WHERE tc.project_id = :pid
                ORDER BY tc.case_number, tc.id
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("\n=== TEST CASES (all) ===")
        for tc in tcs:
            print(dict(tc))

        # Cases per story
        per_story = conn.execute(
            text(
                """
                SELECT us.id, us.external_key, us.title,
                       COUNT(tc.id) AS case_count,
                       SUM(CASE WHEN tc.status = 'ready' THEN 1 ELSE 0 END) AS ready_count,
                       SUM(CASE WHEN tc.is_generated THEN 1 ELSE 0 END) AS ai_generated_count
                FROM user_stories us
                LEFT JOIN test_cases tc ON tc.user_story_id = us.id
                WHERE us.project_id = :pid
                GROUP BY us.id, us.external_key, us.title
                ORDER BY us.id
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("\n=== TEST CASES PER USER STORY ===")
        for row in per_story:
            print(dict(row))

        try:
            jobs = conn.execute(
                text(
                    """
                    SELECT id, status, profile, total_stories, completed_stories,
                           current_story_title, story_ids, coverage_report,
                           created_at, completed_at
                    FROM generation_jobs
                    WHERE project_id = :pid
                    ORDER BY id DESC
                    """
                ),
                {"pid": pid},
            ).mappings().all()
            print("\n=== GENERATION JOBS ===")
            print(f"Count: {len(jobs)}")
            for j in jobs:
                d = dict(j)
                if d.get("coverage_report"):
                    d["coverage_report"] = f"<{len(str(d['coverage_report']))} chars>"
                print(d)
        except Exception as exc:
            print(f"\n=== GENERATION JOBS === (error: {exc})")

        runs = conn.execute(
            text(
                """
                SELECT id, run_number, name, status, total_tests, passed_tests, failed_tests,
                       started_at, completed_at, created_at
                FROM test_runs
                WHERE project_id = :pid
                ORDER BY id DESC
                LIMIT 20
                """
            ),
            {"pid": pid},
        ).mappings().all()
        print("\n=== TEST RUNS (last 20) ===")
        print(f"Count shown: {len(runs)}")
        run_total = conn.execute(
            text("SELECT COUNT(*) FROM test_runs WHERE project_id = :pid"),
            {"pid": pid},
        ).scalar()
        print(f"Total test runs: {run_total}")
        for r in runs:
            print(dict(r))

        try:
            ic = conn.execute(
                text(
                    """
                    SELECT id, status, app_url, overall_status, steps_total, steps_passed,
                           steps_failed, created_at, completed_at
                    FROM integrity_check_results
                    WHERE project_id = :pid
                    ORDER BY id DESC
                    LIMIT 10
                    """
                ),
                {"pid": pid},
            ).mappings().all()
            print("\n=== INTEGRITY CHECKS (last 10) ===")
            ic_total = conn.execute(
                text("SELECT COUNT(*) FROM integrity_check_results WHERE project_id = :pid"),
                {"pid": pid},
            ).scalar()
            print(f"Total integrity checks: {ic_total}")
            for row in ic:
                print(dict(row))
        except Exception as exc:
            print(f"\n=== INTEGRITY CHECKS === (error: {exc})")

        rec_runs = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM test_recommendation_runs WHERE project_id = :pid
                """
            ),
            {"pid": pid},
        ).scalar()
        print(f"\n=== TEST RECOMMENDATION RUNS ===\nTotal: {rec_runs}")


if __name__ == "__main__":
    main()
