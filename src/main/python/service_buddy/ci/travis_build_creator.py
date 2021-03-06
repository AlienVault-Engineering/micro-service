import json
import os

import logging

from service_buddy.service.service import Service
from service_buddy.util.command_util import invoke_process


class TravisBuildCreator(object):

    def options(self):
        return {}

    def init(self, dry_run, default_config, build_templates,user=None, password=None):
        self.dry_run = dry_run
        self.build_templates = build_templates
        self.build_configuration = default_config.get('build-configuration',{})
        self.use_org = default_config.get("use-travis-open-source", True)
        self.gh_token = default_config.get('github-token', os.environ.get('GITHUB_TOKEN',''))
        self.pypi_user = default_config.get('pypi-user', os.environ.get('PYPI_USER'))
        self.pypi_pass = default_config.get('pypi-pass', os.environ.get('PYPI_PASS'))
        self.default_args = ['--no-interactive']
        if self._invoke_travis(['--help'],append_org=False) != 0:
            raise Exception("Travis CLI must be installed to use travis build creator.  "
                            "See https://github.com/travis-ci/travis.rb#installation")
        if self._invoke_travis([ 'login', '--github-token', self.gh_token]) != 0:
            raise Exception("Unable to authenticate Travis CLI. Please verify github token is configured properly.")

    def create_project(self, service_definition, app_dir):
        # type: (Service, str) -> None
        if service_definition.get_service_type() not in self.build_templates:
            raise Exception(
                "Build template not found for service type {}".format(service_definition.get_service_type()))
        else:
            build_type = self.build_templates.get(service_definition.get_service_type())['type']
        service_dir = service_definition.get_service_directory(app_dir=app_dir)
        if os.path.exists(self._get_travis_file(service_dir)):
            logging.warn("travis build file exists - enabling repo")
            self._invoke_travis([ 'enable'], exec_dir=service_dir)
        else:
            build_template = self.build_configuration.get(build_type,None)
            if build_template:
                self.create_build(service_dir, build_template,service_definition)
            else:
                logging.warn("Could not locate build template"
                                             " for build type - {}:{}".format(service_definition.get_service_type(),
                                                                              build_type))


    def _get_travis_file(self, service_dir):
        return os.path.join(service_dir, ".travis.yml")

    @classmethod
    def get_type(cls):
        return "travis"

    def create_build(self, service_dir, build_template, service_definition):
        language_ = build_template.get('language', 'python')
        args = [
            'init',
            language_
        ]
        if language_ == 'python':
            args.append('--python')
            args.append('2.7')

        install_script = build_template.get('install', None)
        if install_script:
            args.append('--install')
            self._append_rendered_arguments(args, install_script, service_definition)

        script = build_template.get('script', None)
        if script:
            args.append('--script')
            self._append_rendered_arguments(args, script, service_definition)

        self._invoke_travis(args, exec_dir=service_dir)
        use_pypi = build_template.get('pypi-deploy', False)
        if use_pypi:
            self._write_deploy_stanza(service_dir)
            self._invoke_travis([ 'encrypt', self.pypi_pass, '--add', 'deploy.password'], exec_dir=service_dir)
        invoke_process(['git', 'add','.travis.yml'],exec_dir=service_dir,dry_run=self.dry_run)
        invoke_process(['git', 'commit','-m','Travis build file - generated by service-buddy'],exec_dir=service_dir,dry_run=self.dry_run)

    @staticmethod
    def _append_rendered_arguments(args, install_script, service_definition):
        if isinstance(install_script, basestring):
            install_script = [install_script]
        for script in install_script:
            if "${" in script:
                # Assume is there is bash style escape we don't python escape.  sucks but the extent of my attention
                args.append("\"{}\"".format(script))
            else:
                args.append("\"{}\"".format(script.format(**service_definition)))

    def _write_deploy_stanza(self, service_dir):
        with open(self._get_travis_file(service_dir), 'a') as build_file:
            build_file.writelines([
                '\n'
                'deploy\n',
                '\tprovider: pypi\n',
                '\tuser: {}\n'.format(self.pypi_user),
                '\tdistributions: sdist bdist_wheel\n',
                '\tserver: https://upload.pypi.org/legacy\n'
            ])

    def _invoke_travis(self, args,exec_dir=None,append_org=True):
        base_args = ['travis']
        base_args.extend(args)
        base_args.extend(self.default_args)
        if append_org: base_args.append( '--org' if self.use_org else '--pro')
        if exec_dir:
            return invoke_process(args=base_args,exec_dir=exec_dir,dry_run=self.dry_run)
        else:
            return invoke_process(args=base_args,dry_run=self.dry_run)
