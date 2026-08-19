"""
windowing module.

Responsibility: 5-second window assignment and temporal indexing. Explicitly does NOT extract features.

*** CRITICAL DISTINCTION: I/O BATCH vs SEMANTIC WINDOW ***
Internal processing chunks may have arbitrary sizes (e.g. reading 50,000 rows at a time for I/O efficiency).
However, the ML system must NEVER interpret "10,000 events" or any other I/O batch size as a temporal or semantic unit.
The 5-second window is the ONLY semantic unit of anomaly detection.

Code-Review / Lint Checklist Item:
[ ] "does this code ever treat a batch size as a temporal boundary?"
"""
