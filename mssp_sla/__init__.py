"""MSSP ticket SLA daily operational brief.

Phase A is fully deterministic: parse tickets, apply explicit SLA rules,
emit findings with evidence, and render a markdown brief. Phase B (AI)
is optional and may run only after verification passes.
"""

__version__ = "0.1.0"
