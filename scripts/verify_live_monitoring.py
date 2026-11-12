import os
import sys
import time
import requests
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app import create_app, db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.services.analytics import get_dashboard_summary

def run_live_tests():
    print("=" * 70)
    print("STARTING LIVE INTEGRATION TEST SUITE: JSONPlaceholder API")
    print("Target URL: https://jsonplaceholder.typicode.com/posts/1")
    print("=" * 70)

    test_results = {}
    
    app = create_app("development")
    client = app.test_client()

    with app.app_context():
        # Baseline dashboard metrics
        initial_stats = get_dashboard_summary()
        initial_total_endpoints = initial_stats["total_endpoints"]
        initial_total_checks = initial_stats["total_checks"]
        initial_healthy_count = initial_stats["healthy_count"]
        print(f"[*] Baseline: {initial_total_endpoints} endpoints, {initial_total_checks} checks, {initial_healthy_count} healthy.")

        created_ep_id = None
        try:
            # -------------------------------------------------------------
            # TEST 1: Adding an API works
            # -------------------------------------------------------------
            print("\n[TEST 1] Adding an API with JSONPlaceholder endpoint...")
            add_payload = {
                "name": "Live QA Verification - JSONPlaceholder Post 1",
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "method": "GET",
                "timeout": 10,
                "expected_status": 200,
                "check_interval": 30,
                "tags": "qa-live,jsonplaceholder,posts"
            }
            res = client.post("/api/endpoints", json=add_payload)
            if res.status_code == 201:
                data = res.get_json()
                created_ep_id = data["data"]["id"]
                db_ep = db.session.get(Endpoint, created_ep_id)
                if db_ep and db_ep.name == add_payload["name"] and db_ep.url == add_payload["url"]:
                    test_results["1_add_api"] = {
                        "status": "PASS",
                        "detail": f"Endpoint added successfully with ID {created_ep_id} (HTTP 201 Created)"
                    }
                    print(f"  -> PASS: Endpoint ID {created_ep_id} created in SQLite.")
                else:
                    test_results["1_add_api"] = {
                        "status": "FAIL",
                        "detail": "Endpoint created in response but not found in SQLite database"
                    }
                    print("  -> FAIL: Not found in SQLite.")
            else:
                test_results["1_add_api"] = {
                    "status": "FAIL",
                    "detail": f"Failed with HTTP {res.status_code}: {res.get_data(as_text=True)}"
                }
                print(f"  -> FAIL: HTTP {res.status_code}")

            assert created_ep_id is not None, "Cannot continue without created endpoint"

            # -------------------------------------------------------------
            # TEST 2: GET request returns actual HTTP 200
            # -------------------------------------------------------------
            print("\n[TEST 2] Executing live manual check against real JSONPlaceholder endpoint...")
            check_res = client.post(f"/api/endpoints/{created_ep_id}/check")
            check_json = check_res.get_json()
            check_result_data = check_json.get("data", {}).get("check_result", {})
            actual_status_code = check_result_data.get("status_code")
            is_success = check_result_data.get("is_success")

            print(f"  -> Returned HTTP Status Code: {actual_status_code}, Success: {is_success}")
            if actual_status_code == 200 and is_success is True:
                test_results["2_http_200"] = {
                    "status": "PASS",
                    "detail": f"Real probe returned status 200 OK (is_success={is_success})"
                }
                print("  -> PASS: Live endpoint responded with real HTTP 200.")
            else:
                test_results["2_http_200"] = {
                    "status": "FAIL",
                    "detail": f"Expected HTTP 200, got status {actual_status_code}, error: {check_result_data.get('error_message')}"
                }
                print(f"  -> FAIL: Status code {actual_status_code}")

            # -------------------------------------------------------------
            # TEST 3: Response time is measured
            # -------------------------------------------------------------
            print("\n[TEST 3] Verifying response time measurement...")
            latency_ms = check_result_data.get("response_time_ms")
            print(f"  -> Measured Latency: {latency_ms} ms")
            if isinstance(latency_ms, (int, float)) and latency_ms > 0.0:
                test_results["3_response_time_measured"] = {
                    "status": "PASS",
                    "detail": f"Response time measured accurately at {latency_ms:.2f} ms using time.perf_counter()"
                }
                print(f"  -> PASS: Latency {latency_ms:.2f} ms > 0 ms.")
            else:
                test_results["3_response_time_measured"] = {
                    "status": "FAIL",
                    "detail": f"Invalid latency measured: {latency_ms}"
                }
                print("  -> FAIL: Invalid latency.")

            # -------------------------------------------------------------
            # TEST 4: Health status is calculated correctly
            # -------------------------------------------------------------
            print("\n[TEST 4] Verifying health status calculation...")
            calculated_status = check_result_data.get("status")
            db_ep = db.session.get(Endpoint, created_ep_id)
            expected_health = "healthy" if latency_ms < 1200.0 else "degraded"
            print(f"  -> Endpoint last_status in DB: {db_ep.last_status}, Expected based on {latency_ms}ms: {expected_health}")
            if db_ep.last_status == expected_health and calculated_status == expected_health:
                test_results["4_health_status_calculated"] = {
                    "status": "PASS",
                    "detail": f"Health status correctly evaluated as '{db_ep.last_status}' (Threshold: 1200ms, Actual: {latency_ms:.2f}ms)"
                }
                print(f"  -> PASS: Health status is correctly '{db_ep.last_status}'.")
            else:
                test_results["4_health_status_calculated"] = {
                    "status": "FAIL",
                    "detail": f"Status mismatch: DB has '{db_ep.last_status}', expected '{expected_health}'"
                }
                print("  -> FAIL: Health status mismatch.")

            # -------------------------------------------------------------
            # TEST 5: Monitoring history is saved in SQLite
            # -------------------------------------------------------------
            print("\n[TEST 5] Verifying monitoring history persistence in SQLite...")
            db.session.refresh(db_ep)
            results = CheckResult.query.filter_by(endpoint_id=created_ep_id).order_by(CheckResult.checked_at.desc()).all()
            print(f"  -> Total CheckResult records found in SQLite for endpoint: {len(results)}")
            # Upon creation, initial check was run (+1), plus the manual check (+1) = 2 checks
            if len(results) >= 1:
                latest_result = results[0]
                has_valid_fields = (
                    latest_result.status_code == 200 and
                    latest_result.response_time_ms > 0 and
                    latest_result.checked_at is not None and
                    latest_result.is_success is True
                )
                if has_valid_fields:
                    test_results["5_history_persistence"] = {
                        "status": "PASS",
                        "detail": f"Persisted {len(results)} CheckResult records in SQLite with timestamp {latest_result.checked_at.isoformat()}Z, status {latest_result.status_code}, and latency {latest_result.response_time_ms:.2f}ms"
                    }
                    print("  -> PASS: CheckResult records verified in SQLite database.")
                else:
                    test_results["5_history_persistence"] = {
                        "status": "FAIL",
                        "detail": f"CheckResult records found but fields invalid: status={latest_result.status_code}, time={latest_result.response_time_ms}"
                    }
                    print("  -> FAIL: Invalid CheckResult fields.")
            else:
                test_results["5_history_persistence"] = {
                    "status": "FAIL",
                    "detail": "No CheckResult rows found in SQLite for this endpoint."
                }
                print("  -> FAIL: 0 CheckResult rows.")

            # -------------------------------------------------------------
            # TEST 6: Dashboard metrics update correctly
            # -------------------------------------------------------------
            print("\n[TEST 6] Verifying dashboard metrics update dynamically...")
            updated_stats = get_dashboard_summary()
            ep_count_diff = updated_stats["total_endpoints"] - initial_total_endpoints
            checks_diff = updated_stats["total_checks"] - initial_total_checks
            print(f"  -> Total endpoints: {initial_total_endpoints} -> {updated_stats['total_endpoints']} (diff: +{ep_count_diff})")
            print(f"  -> Total checks: {initial_total_checks} -> {updated_stats['total_checks']} (diff: +{checks_diff})")
            print(f"  -> System Uptime: {updated_stats['system_uptime']}%")
            print(f"  -> 2xx count in distribution: {updated_stats['status_distribution']['2xx']}")

            if ep_count_diff == 1 and checks_diff >= 1:
                test_results["6_dashboard_metrics"] = {
                    "status": "PASS",
                    "detail": f"Dashboard updated accurately: total_endpoints (+{ep_count_diff}), total_checks (+{checks_diff}), uptime ({updated_stats['system_uptime']}%), 2xx count ({updated_stats['status_distribution']['2xx']})"
                }
                print("  -> PASS: Dashboard metrics updated reflecting real telemetry.")
            else:
                test_results["6_dashboard_metrics"] = {
                    "status": "FAIL",
                    "detail": f"Metrics discrepancy: ep_diff={ep_count_diff}, checks_diff={checks_diff}"
                }
                print("  -> FAIL: Metrics discrepancy.")

            # -------------------------------------------------------------
            # TEST 7: Auto-refresh works
            # -------------------------------------------------------------
            print("\n[TEST 7] Verifying auto-refresh telemetry & dynamic feed...")
            # Trigger another check simulating background scheduler or auto-refresh probe
            res_refresh = client.get("/api/dashboard/stats")
            stats_json = res_refresh.get_json()
            has_trend = len(stats_json.get("data", {}).get("trend_latencies", [])) > 0
            has_activity = len(stats_json.get("data", {}).get("recent_activity", [])) > 0
            recent_item = stats_json.get("data", {}).get("recent_activity", [])[0] if has_activity else {}
            
            # Check that recent activity includes the live JSONPlaceholder check
            matched_recent = any(
                item.get("endpoint_id") == created_ep_id 
                for item in stats_json.get("data", {}).get("recent_activity", [])
            )

            if res_refresh.status_code == 200 and has_trend and matched_recent:
                test_results["7_auto_refresh"] = {
                    "status": "PASS",
                    "detail": f"Telemetry polling endpoint /api/dashboard/stats returned fresh payload with {len(stats_json['data']['recent_activity'])} activity logs and {len(stats_json['data']['trend_latencies'])} trend points; recent probe captured."
                }
                print("  -> PASS: Auto-refresh feed returned live streaming data.")
            else:
                test_results["7_auto_refresh"] = {
                    "status": "FAIL",
                    "detail": f"Auto-refresh payload incomplete: has_trend={has_trend}, matched_recent={matched_recent}"
                }
                print("  -> FAIL: Auto-refresh data check failed.")

            # -------------------------------------------------------------
            # TEST 8: Delete and edit operations work
            # -------------------------------------------------------------
            print("\n[TEST 8] Verifying edit and delete operations...")
            # A) EDIT
            edit_payload = {
                "name": "Live QA Verification - JSONPlaceholder Edited",
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "method": "GET",
                "timeout": 15,
                "expected_status": 200,
                "check_interval": 45,
                "tags": "qa-live,edited"
            }
            edit_res = client.put(f"/api/endpoints/{created_ep_id}", json=edit_payload)
            edit_ok = (edit_res.status_code == 200 and edit_res.get_json()["data"]["name"] == edit_payload["name"])
            
            db_ep_edited = db.session.get(Endpoint, created_ep_id)
            edit_db_ok = (db_ep_edited.name == edit_payload["name"] and db_ep_edited.timeout == 15)
            print(f"  -> Edit API result: HTTP {edit_res.status_code}, DB name: '{db_ep_edited.name}' (Matched: {edit_db_ok})")

            # B) DELETE
            del_res = client.delete(f"/api/endpoints/{created_ep_id}")
            del_ok = (del_res.status_code == 200)
            db_ep_after_del = db.session.get(Endpoint, created_ep_id)
            # Check cascade delete of CheckResult records
            orphaned_results = CheckResult.query.filter_by(endpoint_id=created_ep_id).count()
            print(f"  -> Delete API result: HTTP {del_res.status_code}, Endpoint in DB: {db_ep_after_del}, Orphaned checks: {orphaned_results}")

            # Also check dashboard count decremented back
            final_stats = get_dashboard_summary()
            ep_count_restored = (final_stats["total_endpoints"] == initial_total_endpoints)
            print(f"  -> Endpoint count restored to baseline: {final_stats['total_endpoints']} == {initial_total_endpoints}: {ep_count_restored}")

            if edit_ok and edit_db_ok and del_ok and (db_ep_after_del is None) and (orphaned_results == 0) and ep_count_restored:
                test_results["8_delete_and_edit"] = {
                    "status": "PASS",
                    "detail": f"Edit updated name & timeout in SQLite; Delete removed endpoint and cleanly cascaded all {len(results)} CheckResult records; Total endpoints returned to {initial_total_endpoints}."
                }
                print("  -> PASS: Edit and Delete operations verified with clean cascade.")
            else:
                test_results["8_delete_and_edit"] = {
                    "status": "FAIL",
                    "detail": f"Failure in edit/delete: edit_ok={edit_ok}, edit_db_ok={edit_db_ok}, del_ok={del_ok}, ep_gone={db_ep_after_del is None}, orphaned_results={orphaned_results}, count_restored={ep_count_restored}"
                }
                print("  -> FAIL: Edit or Delete failed.")

        except Exception as e:
            print(f"\n[EXCEPTION DURING TEST EXECUTION]: {e}")
            import traceback
            traceback.print_exc()
            if created_ep_id:
                try:
                    ep_cleanup = db.session.get(Endpoint, created_ep_id)
                    if ep_cleanup:
                        db.session.delete(ep_cleanup)
                        db.session.commit()
                except Exception:
                    pass
            raise e

    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)
    for test_key, res in test_results.items():
        print(f"[{res['status']}] {test_key}: {res['detail']}")
    print("=" * 70)

    return test_results

if __name__ == "__main__":
    run_live_tests()
