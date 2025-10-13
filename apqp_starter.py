"""
DEPRECATED — This legacy CLI entrypoint has been archived.

Please use the FastAPI server and agents workflow instead:
- Server: server/main.py (run with run_server.py)
- Endpoints: /ingest → /agents/run → /qa/grade → /publish
- Agent wrapper: agent/agent.py

This file remains to avoid breaking references but no longer contains runnable code.
"""

print("apqp_starter.py is deprecated. Use the FastAPI server in server/main.py.")
