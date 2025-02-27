#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pocw.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # wrap pytest command here so we don't have to manage
    # PYTHONPATH in multiple places. django-pytest unfortunately
    # doesn't provide native management commands so we still need
    # to invoke pytest directly
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        pytest_args = " ".join(sys.argv[2:])
        os.environ["PYTHONPATH"] = sys.path[0]
        subprocess.run(f"pytest {pytest_args}", shell=True, env=os.environ)
    else:
        execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
