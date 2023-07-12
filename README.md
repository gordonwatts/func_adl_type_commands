# func_adl_type_commands

Command line for building type packages for func_adl

## Usage

Use this command to build python packages with type information for

* ATLAS PHYS/PHYSLITE R21, R22, and R24.

To get help:

```text
(.venv) PS C:\Users\gordo\Code\iris-hep\atlas_types\func_adl_type_commands> atlas_build_type_info --help
usage: test_atlas_release_types [-h] [-v | --verbose | --no-verbose] {build,test} ...

Build and test atlas release types

positional arguments:
  {build,test}          sub-command help
    build               Build type library for a release
    test                Run tests for a release

options:
  -h, --help            show this help message and exit
  -v, --verbose, --no-verbose

This takes a while
(.venv) PS C:\Users\gordo\Code\iris-hep\atlas_types\func_adl_type_commands> 
```

### Setup

1. Check out this package in an empty folder - other directories will be created in this folder (like the packages themselves). For purposes of this discussion the directory is called `atlas_types`.
1. Once checked out, create a `venv`, and use `pip install .` at the root of this package. This `venv` will be only for running commands in this package.
1. If you want to run the tests, you need the test files:
    * Use [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/g/gwatts/public/data/asg_test_data?items-per-page=100&view-mode=resource-table&tiles-size=1) to download the files into a `data` directory in the `atlas_types` directory.
    * Some of these files are [un-necessarily large](https://github.com/gordonwatts/func_adl_type_commands/issues/1).

### Running

After everything is setup above, you can run this. There are two ways. First, to *build* the packages for use:

```bash
python .\test_atlas_release_types.py build 24.2.4
```

This will build the package and leave it in a directory `atlas_types/...`

Also, can do some simple testing to make sure that everything is working properly!

```bash
python .\test_atlas_release_types.py test --test jets_uncalib 24.2.3 --test_dir ..\testing_dir\
```
