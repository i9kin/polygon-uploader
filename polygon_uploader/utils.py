import subprocess
from collections import OrderedDict
from pathlib import Path, PosixPath
from typing import List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import click
from camelot import read_pdf
from polygon_api import FeedbackPolicy, PointsPolicy
from polygon_api.api import GeneratedTest, ManualTest
from prompt_toolkit.validation import ValidationError, Validator
from PyInquirer import Separator, prompt
from rich.table import Table

bad = '\u274C'
good = '\u2713'
XML_PATH = 'problem.xml'
XML_CONTEST_PATH = 'contest.xml'


def get_feedback_policy(group):
    feedback_policy = group.get('feedback-policy')
    if feedback_policy == 'complete':
        return FeedbackPolicy.COMPLETE
    elif feedback_policy == 'icpc':
        return FeedbackPolicy.ICPC
    elif feedback_policy in set('complete', 'NONE'):
        return FeedbackPolicy.COMPLETE
    else:
        click.echo('strange feedback_policy')
        exit(0)


def get_points_policy(group):
    points_policy = group.get('points-policy')
    if points_policy == 'complete-group':
        return PointsPolicy.COMPLETE_GROUP
    else:
        return PointsPolicy.EACH_TEST


def get_group_dependencies(group):
    dependencies = []
    for dependency in group.findall('dependencies/dependency'):
        dependencies.append(dependency.get('group'))
    if not dependencies:
        return None  # very important 5h debug
    return dependencies


def get_contests() -> dict[PosixPath, List[PosixPath]]:
    # Return Dictionary. key - dictionary, value - list of the path's to problem.xml
    contests = {}
    for task in Path('.').glob('**/' + XML_PATH):
        contest_dir = task.parent.parent.parent
        if contest_dir not in contests:
            contests[contest_dir] = []
        contests[contest_dir].append(task)
    return contests


def get_last_test(tasks):
    # Return Dictionary. key - group name, value - polygon_api.api... test
    last_test = {}
    for ind, test in enumerate(tasks):
        if test.group not in last_test:
            last_test[test.group] = []
        last_test[test.group].append(ind)
    for group, last in last_test.items():
        last_test[group] = tasks[last[-1]]
    return last_test


class NumberValidator(Validator):
    def validate(self, document):
        exp = ValidationError(
            message='Please enter a number',
            cursor_position=len(document.text),
        )
        if not document.text.isdecimal():
            raise exp


def validate_dependencies(input_, cur_group, groups):
    exp = ValidationError(message='Please enter a list of groups')
    for group in input_.split():
        if group == cur_group or group not in groups:
            raise exp
    return True


def to_table(scoring):
    table = Table(show_header=True, header_style='bold')
    width = 12
    table.add_column('Подзадача', style='dim', width=width)
    table.add_column('Баллы')
    table.add_column('Необходимые подзадачи', justify='right')
    for row, group in scoring.items():
        table.add_row(
            str(row),
            str(group['score']),
            ', '.join(str(dependence) for dependence in group['dependencies']),
        )
    return table


def find(headers, header):
    for ind, cur_header in enumerate(headers):
        if cur_header.lower() == header.lower():
            return ind


def get_tree(file_path):
    return ElementTree.parse(file_path).getroot()


def group_tag(data, group_number):
    group = Element('group')
    group.set('feedback-policy', 'icpc')
    group.set('points-policy', 'complete-group')
    group.set('name', group_number)
    group.set('points', '{0}.0'.format(data['score']))
    dependencies_tag = Element('dependencies')
    for dependence in data['dependencies']:
        dependence_tag = Element('dependency')
        dependence_tag.set('group', str(dependence))
        dependencies_tag.append(dependence_tag)
    group.append(dependencies_tag)
    return group


def fix_tags(judging):
    for el in judging.findall('groups'):
        judging.remove(el)

    for el in judging.findall('test-points-enabled'):
        judging.remove(el)

    tag = Element('test-points-enabled')
    tag.set('value', 'true')
    judging.append(tag)


def write_scoring(task, scoring):
    # Write scoring to problem.xml.
    tree = get_tree(task / XML_PATH)
    judging = tree.find('judging/testset')
    fix_tags(judging)

    groups = Element('groups')

    for group_number, data in scoring.items():
        groups.append(group_tag(data, group_number))

    judging.append(groups)

    (task / XML_PATH).write_text(
        ElementTree.tostring(tree, encoding='utf-8').decode(),
    )


def get_tables(path_to_task):
    # Return tables from pdf.
    # TODO : some for another languages
    file = path_to_task / 'statements' / '.pdf' / 'russian' / 'problem.pdf'
    return read_pdf(str(file), pages='all', split_text=True)


def detect_score(path_to_task):
    # Detect scoring from pdf table.
    # https://github.com/citxx/polygon-py/blob/master/polygon_api/api.py#L777
    for table in get_tables(path_to_task):
        if table.df.values[0][0].lower() != 'подзадача':
            continue
        headers = table.df.values[0].tolist()
        dependency_col = find(headers, 'Необходимые подзадачи')
        if dependency_col is None:
            dependency_col = find(headers, 'Необходимые\nподзадачи')
        dict = OrderedDict()
        dict['0'] = {
            'score': 0,
            'dependencies': [],
            'type': 'COMPLETE_GROUP',
        }
        for line in table.df.values[1:]:
            if line[0] == '':
                continue
            dict[line[find(headers, 'Подзадача')]] = {
                'score': int(line[find(headers, 'Баллы')]),
                'dependencies': get_dependencies(line, dependency_col),
                'type': 'COMPLETE_GROUP',
            }
        return dict
    return {}


def get_dependencies(line, dependency_col):
    # Get dependencies from string line.
    dependencies = []
    if dependency_col is not None:
        if '–' in line[dependency_col]:
            start, end = line[dependency_col].split('–')
            dependencies = list(range(start, end + 1))
        elif line[dependency_col]:
            dependencies = [
                int(dependence)
                for dependence in line[dependency_col].split(',')
            ]
    return dependencies


def task_status(task):
    root = get_tree(task)
    author = root.get('url').split('/')[-2]
    has_groups = bool(root.find('judging/testset/groups'))
    return has_groups, author


def input_groups(task):
    # Manual input for all subgroups.
    tree = get_tree(task / XML_PATH)
    groups = set()
    for test in tree.find('judging/testset/tests'):
        group = test.get('group')
        if group is not None:
            groups.add(group)
    click.echo('task has groups = {0}'.format(', '.join(sorted(groups))))

    scoring = OrderedDict()
    for group in sorted(groups):
        score = input_scoring(group)
        dependencies = input_dependencies(group, groups)
        scoring[group] = {
            'score': int(score),
            'dependencies': [
                int(dependence) for dependence in dependencies.split()
            ],
            'type': 'COMPLETE_GROUP',
        }
    return scoring


def input_number(message, validate=NumberValidator, filter=int):
    question = prompt(
        [
            {
                'type': 'input',
                'name': 'number',
                'message': message,
                'validate': validate,
                'filter': filter,
            },
        ],
    )
    if not question:
        exit(0)
    return question['number']


def input_confirm(message):
    question = prompt(
        [
            {
                'type': 'confirm',
                'name': 'valid',
                'message': message,
            },
        ],
    )
    if not question:
        exit(0)
    return question['valid']


def input_dependencies(group, groups):
    return input_number(
        'dependencies for group {0}'.format(group),
        validate=lambda input_: validate_dependencies(input_, group, groups),
        filter=str,
    )


def input_scoring(group):
    # Input scoring with validating.
    return input_number('scoring for {0}'.format(group))


def input_polygon_id(api):
    # Input polygon task id with validating.
    polygon_id = input_number('Input you polygon id')
    click.echo('problems.list id = {0}'.format(polygon_id))
    if not api.problems_list(id=polygon_id):
        click.echo('problem {0} not found'.format(polygon_id))
        exit(0)
    return polygon_id


def bad_good(eq):
    return click.style(good, fg='green') if eq else click.style(bad, fg='red')


def polygon_cli_hook(polygon_id, task_path):
    if input_confirm('Load package with polygon-cli?'):
        subprocess.check_call(['polygon-cli', 'init', str(polygon_id)])
        subprocess.check_call(['polygon-cli', 'import_package', task_path])


def cli_choises(tasks):
    choices = []
    for task in tasks:
        has_scoring, author = task_status(task)
        choices.append(
            {
                'name': '{has_scoring} {dir} ({author})'.format(
                    has_scoring=good if has_scoring else bad,
                    dir=task.parent.name,
                    author=author,
                ),
            },
        )
    return choices


def select_task(choices):
    question = prompt(
        [
            {
                'type': 'list',
                'message': 'Select task',
                'name': 'items',
                'choices': choices,
            },
        ],
    )
    if not question:
        exit(0)
    return question['items'][2:].split()[0]


def choice():
    # Selection task menu.
    choices = []
    all_tasks = []
    for contest_dir, tasks in get_contests().items():
        if (contest_dir / XML_CONTEST_PATH).exists():
            task_names = []
            tree = get_tree(contest_dir / XML_CONTEST_PATH)
            choices.append(
                Separator('==' + tree.find('names/name').get('value'))
            )
            for problem in tree.findall('problems/problem'):
                task_names.append(problem.get('url').split('/')[-1])
            tmp = [None for _ in range(len(tasks))]
            for task in tasks:
                tmp[find(task_names, task.parent.name)] = task
            tasks = tmp
        all_tasks += tasks
        choices += cli_choises(tasks)

    task_name = select_task(choices)
    for task in all_tasks:
        if task.parent.name == task_name:
            return task.parent


def save_groups(problem, task_path):
    problem.enable_points(True)
    problem.enable_groups('tests', True)
    last_test = get_last_test(problem.tests('tests'))
    for group in get_tree(task_path / XML_PATH).findall(
        'judging/testset/groups/group'
    ):
        problem.save_test_group(
            'tests',
            group.get('name'),
            points_policy=get_points_policy(group),
            feedback_policy=get_feedback_policy(group),
            dependencies=get_group_dependencies(group),
        )
        save_test(problem, last_test[group.get('name')], group.get('points'))


def save_test(problem, test, points):
    # Save test settings. Uses polygon API.
    if isinstance(test, ManualTest):
        test_input = test.input
    elif isinstance(test, GeneratedTest):
        test_input = test.script_line
    else:
        click.echo('strange type of tests')
        exit(0)
    problem.save_test(
        'tests',
        test.index,
        test_input,
        test_group=test.group,
        test_points=points,
        test_description=test.description,
        test_use_in_statements=test.use_in_statements,
        test_input_for_statements=test.input_for_statements,
        test_output_for_statements=test.output_for_statements,
        verify_input_output_for_statements=test.verify_input_output_for_statements,
    )
