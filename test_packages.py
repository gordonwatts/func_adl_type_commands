# Test type packages with some simple functionality

import argparse
import logging
import tempfile
import time

from func_adl_servicex import SXLocalxAOD
from servicex import ignore_cache

# Try to import one of the releases for testing.
# Hopefully, only one is installed in the environment!
try:
    from func_adl_servicex_xaodr21 import atlas_release, calib_tools
    from func_adl_servicex_xaodr21.event_collection import Event
except Exception:
    try:
        from func_adl_servicex_xaodr22 import atlas_release, calib_tools  # type: ignore
        from func_adl_servicex_xaodr22.event_collection import Event  # type: ignore
    except Exception:
        from func_adl_servicex_xaodr24 import atlas_release, calib_tools  # type: ignore
        from func_adl_servicex_xaodr24.event_collection import Event  # type: ignore

# Based on the release, we will use only one of the test data files
major_release = atlas_release.split(".")[0]

# Setup config
release_config = {
    "21": [
        {
            "file": r"C:\Users\gordo\Code\atlas\data\asg\mc_311321_physVal_Main.21.2.143.pool.root",
            "calibration": "PHYS",
            "jet_bank": "AntiKt4EMPFlowJets",
        }
    ],
    "22": [
        {
            "file": r"C:\Users\gordo\Code\atlas\data\asg\mc_410470_ttbar.DAOD_PHYS.22.2.110.pool.root.1",
            "calibration": "PHYS",
            "jet_bank": "AntiKt4EMPFlowJets",
        },
        {
            "file": r"C:\Users\gordo\Code\atlas\data\asg\mc20_13TeV.410470.PhPy8EG_A14_ttbar_hdamp258p75_nonallhad.22.2.113.pool.root",
            "calibration": "PHYSLITE",
            "jet_bank": "AnalysisJets",
        },
    ],
}
release_config["24"] = release_config["22"]


def make_uncalibrated_jets_plot(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    jets = (
        ds.SelectMany(lambda e: e.Jets(calibrate=False))
        .Select(lambda j: j.pt())
        .as_awkward()
        .value()
    )
    print(jets)


def make_calibrated_jets_plot(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    jets = (
        ds.SelectMany(lambda e: e.Jets()).Select(lambda j: j.pt()).as_awkward().value()
    )
    print(jets)


def make_calibrated_met_plot(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    jets = (
        ds.SelectMany(lambda e: e.MissingET())
        .Select(lambda met: met.met())
        .as_awkward()
        .value()
    )
    print(jets)


# If called from the command line
if __name__ == "__main__":
    # Get around a bug in how xAODDataset makes sure everything is ok.
    # TODO: Fix this bug in wherever it needs to be fixed.
    logging.debug(
        f"Fetching tempdir to prevent bug in xAODDataset {tempfile.gettempdir()}"
    )

    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        prog="test_packages",
        description="Run tests against local SX in current venv",
        epilog="Tests, especially calibrated ones, can take a while to execute",
    )
    parser.add_argument("-v", "--verbose", default=False, action="count")
    parser.add_argument(
        "--test",
        help="Which tests should be run?",
        choices=["jets_uncalib", "jets_calib", "met"],
        action="append",
        default=[],
    )

    args = parser.parse_args()

    logging.basicConfig()
    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build the dataset we will use for testing.
    release_info_list = release_config[major_release]
    for release_info in release_info_list:
        data_file = release_info["file"]
        data_format = release_info["calibration"]
        ds = SXLocalxAOD[Event](
            data_file,
            item_type=Event,
            docker_image="gitlab-registry.cern.ch/atlas/athena/analysisbase",
            docker_tag=atlas_release,
        )
        ds = calib_tools.query_update(ds, calib_tools.default_config(data_format))
        logging.info(f"Using atlas release {atlas_release}")

        # Now, lets run on the files for tests.
        for t in args.test:
            start = time.time()
            with ignore_cache():
                if t == "jets_uncalib":
                    make_uncalibrated_jets_plot(ds)
                elif t == "jets_calib":
                    make_calibrated_jets_plot(ds)
                elif t == "met":
                    make_calibrated_met_plot(ds)
                else:
                    raise NotImplementedError(f"Unknown test {t}")
            end = time.time()
            logging.info(f"{t}: {end - start:0.2f} seconds")
