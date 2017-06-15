import argparse
import logging

from lib.initializer import Initializer
from lib.log_handler import configure_logging
from lib.services import load_service_definitions, pretty_print_services
from lib.vcs import VCS

LIST = 'list'
SYNC = 'sync'
PULL = 'pull'
parser = argparse.ArgumentParser(prog="service-manager", description='Utility to help deploy and manage microservices.')

parser.add_argument('--verbose', help='Level of logging to output', action="store_true", default=False)
parser.add_argument('--application-filter', help='Constrain to passed application', type=str, default=None)
parser.add_argument('--vcs-user', help='Username for VCS', type=str, default=None, required=True)
parser.add_argument('--vcs-password', help='Password for VCS', type=str, default=None, required=True)
parser.add_argument('--vcs-root-url', help='Root url for git repos', type=str, required=True)
parser.add_argument('--service-directory', help='Directory containing service definitions in <app>/service.json format', type=str, default='../../../../services')
parser.add_argument('--dry-run',help='Preview effect of action', action="store_true",
                         default=False)
subparsers = parser.add_subparsers(help='commands')

list_parser = subparsers.add_parser(LIST, help='List known services')
list_parser.set_defaults(command=LIST)
list_parser.add_argument('--validate-repository', help='Validate existence of repository in VCS', action="store_true",
                         default=False)
sync_parser = subparsers.add_parser(SYNC, help='Sync service definitions and initialize new entries.')
sync_parser.set_defaults(command=SYNC)
sync_parser.add_argument('--destination-directory',help='Destination directory to create new service definition.',required=True)

pull_parser = subparsers.add_parser(PULL, help='Pull git repos into local filesystem.')
pull_parser.set_defaults(command=PULL)
pull_parser.add_argument('--destination-directory',help='Destination directory to pull code into.',required=True)


def execute_main():
    args = parser.parse_args()
    configure_logging(args.verbose)
    application_map = load_service_definitions(args.application_filter, args.service_directory)
    vcs = VCS(args.vcs_user, args.vcs_password, args.repo_root, args.dry_run)
    if args.command == LIST:
        if args.validate_repository:
            vcs.validate_repositories(application_map)
        pretty_print_services(application_map)
    elif args.command == SYNC:
        vcs.validate_repositories(application_map)
        init = Initializer(vcs, args.destination_directory, args.dry_run)
        init.initialize_services(application_map)
    elif args.command == PULL:
        vcs.validate_repositories(application_map)
        vcs.pull_services(application_map, args.destination_directory)


if __name__ == "__main__":
    execute_main()
