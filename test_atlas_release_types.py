import argparse
import logging
import subprocess
from pathlib import Path
from typing import List


def run_command(cmd: str | List[str]):
    """Run a command and dump the resulting output to logging,
    depending on the return code.

    Args:
        cmd (str): Command to run
    """
    if isinstance(cmd, list):
        cmd = ";".join(cmd)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    level = logging.INFO
    if result.returncode != 0:
        level = logging.ERROR

    logging.log(level, f"Result code from running {cmd}: {result.returncode}")
    for line in result.stdout.split("\n"):
        logging.log(level, f"stdout: {line}")
    for line in result.stderr.split("\n"):
        logging.log(level, f"stderr: {line}")


def create_type_json(release: str, clean: bool, location: Path) -> Path:
    """Create the type json file for a release.

    Args:
        release (_type_): Release name - an image tag
        clean (_type_): If true, then refresh even if yaml file is present.
    """
    logging.info(f"Building JSON file for {release}")

    # Can we skip?
    yaml_path = location / f"{release}.yaml"
    if yaml_path.exists() and (not clean):
        logging.info(f"YAML type file for {release} already exists. Not rebuilding")
        return yaml_path

    # Do the build.
    logging.info(f"Running container to build json type file for {release}")
    run_command(
        "powershell ../../func-adl-types-atlas/scripts/build_xaod_edm.ps1"
        f" {release} {yaml_path}"
    )
    logging.info(f"Finished building json type file for {release}")

    return yaml_path


def create_python_package(
    release: str, clean: bool, json_location: Path, location: Path
) -> Path:
    """Given the type json file already exists, create the python
    package for the full type information.

    Args:
        release (str): The name of the release
        clean (bool): If true, remake the package from scratch.
                    Otherwise, only if it isn't there already.
        json_location (Path): Location of the json yaml file
        location (Path): Directory to house the created package

    Returns:
        Path: Location of the package
    """
    logging.info(f"Creating python package for release {release}")

    # See if we can bail out quickly
    package_location = location / release
    if package_location.exists() and (not clean):
        logging.info(
            f"Python package for release {release} already exists. Not rebuilding."
        )
        return package_location

    # Re-create it.
    commands = []
    commands.append(
        r"powershell -c . c:\Users\gordo\Code\iris-hep\venv\Scripts\Activate.ps1"
    )
    commands.append(r"cd c:\Users\gordo\Code\iris-hep\func_adl_servicex_type_generator")
    commands.append(
        f"poetry run sx_type_gen {json_location.absolute()} --output_directory"
        f" {package_location.absolute()}"
    )
    run_command(commands)

    return package_location


def do_build(args):
    for r in args.release:
        yaml_location = create_type_json(r, args.clean, args.type_json)
        create_python_package(r, args.clean, yaml_location, args.type_package)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="test_atlas_release_types",
        description="Build and test atlas release types",
        epilog="This takes a while",
    )
    parser.add_argument(
        "-v", "--verbose", default=False, action=argparse.BooleanOptionalAction
    )

    commands = parser.add_subparsers(help="sub-command help")

    # The "build" an atlas release command
    build_command = commands.add_parser(
        "build", help="Build type library for a release"
    )
    build_command.add_argument(
        "release", type=str, help="List of releases to build", action="append"
    )
    build_command.add_argument(
        "--clean", type=bool, action=argparse.BooleanOptionalAction, default=False
    )
    build_command.add_argument(
        "--type_json",
        type=Path,
        default=Path("../type_files"),
        help="Location where yaml type files should be written",
    )
    build_command.add_argument(
        "--type_package",
        type=Path,
        default=Path(
            "../type_packages",
            help="Location where the python type package should be created",
        ),
    )
    build_command.set_defaults(func=do_build)

    args = parser.parse_args()

    # Global flags
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)

    # Now execute the command
    args.func(args)
