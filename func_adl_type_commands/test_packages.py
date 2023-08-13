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
except Exception as e:
    logging.info(f"Failed to load r21: {str(e)}")
    try:
        from func_adl_servicex_xaodr22 import atlas_release, calib_tools  # type: ignore
        from func_adl_servicex_xaodr22.event_collection import Event  # type: ignore
    except Exception:
        logging.info(f"Failed to load r22: {str(e)}")
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
            "uncalib_ok": True,
        }
    ],
    "22": [
        {
            "file": r"C:\Users\gordo\Code\atlas\data\asg\mc_410470_ttbar.DAOD_PHYS.22.2.110.pool.root.1",
            "calibration": "PHYS",
            "jet_bank": "AntiKt4EMPFlowJets",
            "uncalib_ok": True,
        },
        {
            "file": r"C:\Users\gordo\Code\atlas\data\asg\mc20_13TeV.410470.PhPy8EG_A14_ttbar_hdamp258p75_nonallhad.22.2.113.pool.root",
            "calibration": "PHYSLITE",
            "jet_bank": "AnalysisJets",
            "uncalib_ok": False,
        },
    ],
}
release_config["24"] = release_config["22"]


def make_uncalibrated_jets_plot(ds: SXLocalxAOD[Event], uncalib_ok: bool = True):
    "Get the uncalibrated jets data from a file"
    try:
        logging.info("Starting uncalibrated jets test")
        jets = (
            ds.SelectMany(lambda e: e.Jets(calibrate=False))
            .Select(lambda j: j.pt())
            .as_awkward()
            .value()
        )
        logging.info(jets)
    except NotImplementedError as e:
        if uncalib_ok:
            raise
        if "Requested uncalibrated" in str(e):
            logging.info("Caught expected exception for uncalibrated jets: {e}")


def error_bad_argument(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    try:
        (
            ds.SelectMany(lambda e: e.Jets(calibrated=False))
            .Select(lambda j: j.pt())
            .as_awkward()
            .value()
        )
        raise RuntimeError("Should have thrown an exception with bad argument")
    except TypeError as e:
        if "calibrated" not in str(e):
            raise
        logging.info("Caught expected exception for bad call to Jets method: {e}")


def make_calibrated_jets_plot(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    logging.info("Starting calibrated jets test")
    jets = (
        ds.SelectMany(lambda e: e.Jets()).Select(lambda j: j.pt()).as_awkward().value()
    )
    logging.info(jets)


def make_calibrated_met_plot(ds: SXLocalxAOD[Event]):
    "Get the uncalibrated jets data from a file"
    logging.info("Starting calibrated MET test")
    jets = (
        ds.SelectMany(lambda e: e.MissingET())
        .Select(lambda met: met.met())
        .as_awkward()
        .value()
    )
    logging.info(jets)


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
        choices=["jets_uncalib", "jets_calib", "met", "error_bad_argument"],
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
        uncalib_ok = release_info["uncalib_ok"]
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
                    make_uncalibrated_jets_plot(ds, uncalib_ok=uncalib_ok)
                elif t == "jets_calib":
                    make_calibrated_jets_plot(ds)
                elif t == "met":
                    make_calibrated_met_plot(ds)
                elif t == "error_bad_argument":
                    error_bad_argument(ds)
                else:
                    raise NotImplementedError(f"Unknown test {t}")
            end = time.time()
            logging.info(f"{t}: {end - start:0.2f} seconds")
