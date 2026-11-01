"""SQLite store for pipeline runs, deployments and test outcomes."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS commits (
    sha TEXT PRIMARY KEY, committed_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stage_runs (
    id INTEGER PRIMARY KEY, sha TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
    seconds REAL NOT NULL);
CREATE TABLE IF NOT EXISTS deployments (
    id INTEGER PRIMARY KEY, sha TEXT NOT NULL, env TEXT NOT NULL, deployed_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS test_attempts (
    sha TEXT NOT NULL, test TEXT NOT NULL, attempt INT NOT NULL, passed INT NOT NULL,
    PRIMARY KEY (sha, test, attempt));
CREATE TABLE IF NOT EXISTS quarantine (
    test TEXT PRIMARY KEY, since REAL NOT NULL, flake_score REAL NOT NULL);
"""


class PipelineStore:
    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)

    def add_commit(self, sha, committed_at):
        self.con.execute("INSERT OR REPLACE INTO commits VALUES (?, ?)", (sha, committed_at))
        self.con.commit()

    def add_stage(self, sha, stage, status, seconds):
        self.con.execute("INSERT INTO stage_runs (sha, stage, status, seconds) VALUES (?,?,?,?)",
                         (sha, stage, status, seconds))
        self.con.commit()

    def add_deploy(self, sha, env, deployed_at):
        self.con.execute("INSERT INTO deployments (sha, env, deployed_at) VALUES (?,?,?)",
                         (sha, env, deployed_at))
        self.con.commit()

    def add_attempt(self, sha, test, attempt, passed):
        self.con.execute("INSERT OR REPLACE INTO test_attempts VALUES (?,?,?,?)",
                         (sha, test, attempt, int(passed)))
        self.con.commit()

    def close(self):
        self.con.close()
