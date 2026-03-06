"""
Pytest configuration - runs before test collection.
Define TEST_DATABASE_URL=sqlite:///:memory: apenas para testes unitários,
permitindo rodar sem PostgreSQL (ex.: CI, dev local).
"""
import os


def pytest_configure(config):
    """Usa SQLite em memória para unit tests quando TEST_DATABASE_URL não está definido."""
    if "TEST_DATABASE_URL" in os.environ:
        return
    args = getattr(config, "invocation_params", None)
    if args and hasattr(args, "args"):
        paths = " ".join(str(a) for a in args.args)
    else:
        paths = " ".join(str(a) for a in getattr(config, "args", []))
    if "unit" in paths and "integration" not in paths:
        os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
