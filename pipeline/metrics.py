"""Delivery metrics from the SQLite store.

Lead time: seconds from a commit's committed_at to its first staging deployment.
Deployment frequency: staging deployments per day over the observed window.
Values are only as real as the records in the store (see README for what was simulated).
"""
import statistics


def lead_times(store):
    rows = store.con.execute(
        "SELECT c.committed_at, MIN(d.deployed_at) FROM commits c JOIN deployments d "
        "ON d.sha = c.sha AND d.env = 'staging' GROUP BY c.sha").fetchall()
    return sorted(d - c for c, d in rows)


def deployment_frequency_per_day(store):
    (first, last), n = store.con.execute(
        "SELECT MIN(deployed_at), MAX(deployed_at) FROM deployments WHERE env='staging'").fetchone(), \
        store.con.execute("SELECT COUNT(*) FROM deployments WHERE env='staging'").fetchone()[0]
    if n == 0 or last == first:
        return None
    return n / ((last - first) / 86400)


def summary(store):
    lt = lead_times(store)
    if not lt:
        return {"lead_time_seconds": None, "deployments_per_day": None}
    p90 = lt[min(len(lt) - 1, int(0.9 * (len(lt) - 1)))]
    return {
        "deployed_commits": len(lt),
        "lead_time_seconds": {"median": round(statistics.median(lt), 2), "p90": round(p90, 2)},
        "deployments_per_day": round(deployment_frequency_per_day(store) or 0, 3),
    }
