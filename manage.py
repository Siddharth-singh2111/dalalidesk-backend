#!/usr/bin/env python
import os
import click
import subprocess

@click.group()
def cli():
    """Database migration commands."""
    pass

@cli.command()
def init():
    """Initialize database tables."""
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)

@cli.command()
def migrate():
    """Generate migration script."""
    subprocess.run(['alembic', 'revision', '--autogenerate', '-m', "migration"], check=True)

@cli.command()
def upgrade():
    """Apply all migrations."""
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)

if __name__ == '__main__':
    cli()
