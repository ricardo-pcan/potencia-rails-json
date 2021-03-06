# -*- coding: utf-8 -*-
import sys
import json
import os
from fabric.api import cd, env, run, task, require, sudo, local
from fabric.colors import green, red, white, yellow, blue
from fabric.contrib.console import confirm
from fabric.contrib.files import exists
from fabric.operations import get
from fabric import state
from fabutils import boolean
from datetime import date
from time import gmtime, strftime

from fabutils.env import set_env_from_json_file
from fabutils.tasks import ursync_project, ulocal, urun


@task
def environment(env_name, debug=False):
    """
    Creates the configurations for the environment in which tasks will run.
    """
    schemas_dir = "conf/json_schemas/"
    state.output['running'] = boolean(debug)
    state.output['stdout'] = boolean(debug)
    print "Establishing environment " + blue(env_name, bold=True) + "..."
    try:
        set_env_from_json_file(
            'environments.json',
            env_name,
            schemas_dir + "environment_schema.json"
        )
        env.env_name = env_name
        env.confirm_task = True
        env.is_vagrant = False
        if env_name == "vagrant":
            result = ulocal('vagrant ssh-config | grep IdentityFile',
                            capture=True)
            env.key_filename = result.split()[1].replace('"', '')
            env.is_vagrant = True

    except ValueError:
        print red("environments.json has wrong format.", bold=True)
        sys.exit(1)

@task
def sync_files():
    """
    Sync modified files and establish necessary permissions in selected environment.
    """
    require('group', 'public_dir')

    print white("Uploading code to server...", bold=True)
    ursync_project(
        local_dir='./src/',
        remote_dir=env.public_dir,
        exclude=env.exclude,
        delete=True,
        default_opts='-chrtvzP'
    )

    print white("Estableciendo permisos...", bold=True)
    run('chgrp -R {0} {1}'.format(env.group, env.public_dir))
    print green(u'Successfully sync.')

@task
def export_data(file_name="backup-" + strftime("%Y-%m-%d", gmtime())):
    """
    Build database backup
    """
    require('cpchuy_dir', 'dbuser', 'dbpassword', 'dbname', 'dbhost')

    print white("Build database backup...", bold=True)
    export = True
    env.file_name = file_name

    if exists('{cpchuy_dir}database/{file_name}'.format(**env)):
        export = confirm(
            yellow(
                '{cpchuy_dir}database/{file_name} '.format(**env)
                +
                'already exists, Do you want to overwrite it?'
            )
        )

    if export:
        print "Exporting data to file: " + blue(file_name, bold=True) + "..."
        run(
            """
            pg_dump {dbname} \
            > {cpchuy_dir}database/{file_name}
            """.format(**env)
        )
    else:
        print 'Export canceled by user'
        sys.exit(0)

    print green(u'Successfully sync.')

@task
def execute(command=""):
    env.command = command
    with cd('{public_dir}'.format(**env)):
        run('{command}'.format(**env))
