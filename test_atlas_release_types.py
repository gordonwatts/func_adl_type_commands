import argparse
import logging
import subprocess
from pathlib import Path
import sys
from typing import List
import tempfile
import shutil

test_valid = ["jets_uncalib", "jets_calib", "met"]


def run_command(cmd: str | List[str]):
    """Run a command and dump the resulting output to logging,
    depending on the return code.

    Args:
        cmd (str): Command to run
    """
    if not isinstance(cmd, list):
        cmd = [cmd]

    command_line = "powershell -c " + ";".join(cmd)

    try:
        result = subprocess.run(
            command_line,
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
    except Exception:
        logging.error("Exception was thrown running the following commands:")
        for ln in cmd:
            logging.error(f"  {ln}")
        raise


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
        "../../func-adl-types-atlas/scripts/build_xaod_edm.ps1"
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
    commands.append(r". c:\Users\gordo\Code\iris-hep\venv\Scripts\Activate.ps1")
    commands.append(r"cd c:\Users\gordo\Code\iris-hep\func_adl_servicex_type_generator")
    commands.append(
        f"poetry run sx_type_gen {json_location.absolute()} --output_directory"
        f" {package_location.absolute()}"
    )
    run_command(commands)

    # Next we need to find the package - the actual name of the folder might vary a little bit
    # Due to the release series.

    return package_location


def do_build_for_release(release, args):
    yaml_location = create_type_json(release, args.clean, args.type_json)
    return create_python_package(release, args.clean, yaml_location, args.type_package)


def do_build(args):
    """Iterator that builds a package for each release.

    Args:
        args (): Command line arguments

    Yields:
        Path: THe path where the package is located
    """
    for r in args.release:
        do_build_for_release(r, args)
    return 0


def do_test(args):
    """After making sure that the packages are built, run the requested tests

    Args:
        args (): Command line arguments
    """
    for r in args.release:
        package_path = do_build_for_release(r, args)

        # Build the commands to create the env and setup/run the test.
        commands = []

        test_packages_path = Path("test_packages.py")
        assert test_packages_path.exists()

        with tempfile.TemporaryDirectory() as release_dir_tmp:
            release_dir = release_dir_tmp if args.test_dir is None else args.test_dir

            commands.append(f"cd {release_dir}")
            commands.append("python -m venv .venv")
            commands.append(". .venv/Scripts/Activate.ps1")
            commands.append("python -m pip install --upgrade pip")

            # Install the package. We want to run locally, so need to install
            # a special flavor of func_adl_servicex.
            commands.append("python -m pip install func_adl_servicex[local]")
            commands.append(f"python -m pip install -e {package_path.absolute()}")

            # Copy over the script to make it easy to "run".
            shutil.copy(test_packages_path.absolute(), release_dir)

            # Commands to run the scripts
            all_tests = args.test if len(args.test) > 0 else test_valid
            test_args = " ".join([f"--test {t}" for t in all_tests])
            verbose_arg = " -v" if args.verbose else ""

            commands.append(f"python test_packages.py {test_args}{verbose_arg}")

            # Finally, run the commands.
            run_command(commands)
    return 0


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

    def add_build_args(parser):
        parser.add_argument(
            "release", type=str, help="List of releases to build", action="append"
        )
        parser.add_argument(
            "--clean", type=bool, action=argparse.BooleanOptionalAction, default=False
        )
        parser.add_argument(
            "--type_json",
            type=Path,
            default=Path("../type_files"),
            help="Location where yaml type files should be written",
        )
        parser.add_argument(
            "--type_package",
            type=Path,
            default=Path(
                "../type_packages",
                help="Location where the python type package should be created",
            ),
        )

    add_build_args(build_command)
    build_command.set_defaults(func=do_build)

    # The test command
    test_command = commands.add_parser("test", help="Run tests for a release")
    test_command.add_argument("--test", choices=test_valid, default=[], action="append")
    test_command.add_argument(
        "--test_dir",
        type=Path,
        help="Path to place (and leave) test directory",
        default=None,
    )
    add_build_args(test_command)
    test_command.set_defaults(func=do_test)

    args = parser.parse_args()

    # Global flags
    logging.basicConfig()
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Now execute the command
    sys.exit(args.func(args))
