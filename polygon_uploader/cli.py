from __future__ import print_function, unicode_literals

import webbrowser

import click
from rich import print as rprint

from .authentication import authenticate
from .utils import (bad_good, choice, detect_score, get_contests, get_tree,
                       input_confirm, input_groups, input_polygon_id,
                       polygon_cli_hook, save_groups, task_status, to_table,
                       write_scoring)


@click.group()
def cli():
    pass


@cli.command()
def status():
    # Show status for all polygon packages.
    for contest_dir, tasks in get_contests().items():
        char = ''
        if (contest_dir / 'contest.xml').exists():
            click.echo(
                '{name} ({dir})'.format(
                    name=get_tree(contest_dir / 'contest.xml')
                        .find('names/name')
                        .get('value'),
                    dir=contest_dir,
                ),
            )
            char = '\t '
        for task in tasks:
            has_scoring, author = task_status(task)
            click.echo(
                '{char}{has_scoring} {dir} ({author})'.format(
                    char=char,
                    has_scoring=bad_good(has_scoring),
                    dir=task.parent.name,
                    author=author,
                ),
            )


@cli.command()
def load():
    # Load package to polygon.codeforces.com. Uses polygon API for scoring.
    # https://github.com/citxx/polygon-py/blob/master/polygon_api/api.py#L785
    task_path = choice()
    api = authenticate()
    polygon_id = input_polygon_id(api)
    polygon_cli_hook(polygon_id, task_path)
    save_groups(api.problems_list(id=polygon_id)[0], task_path)


@cli.command()
def scoring():
    # Rewrite new scoring for the task.
    # At first, pdf read scoring table. Second, you can input your own scoring.
    task = choice()
    has_scoring, author = task_status(task / 'problem.xml')
    click.echo(
        '{has_scoring} {dir} ({author})'.format(
            has_scoring=bad_good(has_scoring),
            dir=task.name,
            author=author,
        ),
    )
    if has_scoring:
        click.echo('task has a scoring')
    if not input_confirm('Do you create new scoring in problem.xml?'):
        return
    webbrowser.open_new_tab(
        str(task / 'statements' / '.pdf' / 'russian' / 'problem.pdf'),
    )
    old_scoring = detect_score(task)
    rprint(to_table(old_scoring))
    if not input_confirm('Valid scoring?'):
        new_scoring = input_groups(task)
        rprint(to_table(new_scoring))
        write_scoring(task, new_scoring)
    else:
        write_scoring(task, old_scoring)


def main():
    cli()
