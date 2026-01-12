from base_logger import logger
import httpx

# Max number of versions to be fetched in each version branch
MAX_ALLOWED_VERSIONS = 3
VERSIONS_API = "https://downloads.mariadb.org/rest-api/mariadb/"
VERSION_RESOURCE_API = "https://downloads.mariadb.org/rest-api/mariadb/{version}/"
oneinstack_compatible_versions = ["5.5", "10.5", "10.4", "10.11"]


def make_cache() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return_list = []
    latest_meta = []
    live_version_branches = [b["release_id"] for b in httpx.get(VERSIONS_API).json()["major_releases"]
                             if b["release_status"] == "Stable" and b["release_support_type"] == "Long Term Support"]
    version_branches = list(set(oneinstack_compatible_versions + live_version_branches))
    version_branches.sort(reverse=True)
    logger.info(f"Available MariaDB versions: {version_branches}")
    for version in version_branches:
        logger.info(f"Fetching MariaDB version {version}")
        this_branch_latest_meta = {
            "version_file_name": f"mariadb{version.replace(".", "")}_ver",
            "version": None
        }
        this_version_packages = []
        rsp = httpx.get(VERSION_RESOURCE_API.format(version=version)).json()
        patch_list = list(rsp["releases"].values())
        for patch in patch_list:
            try:
                linux_package = [f for f in patch["files"] if f["os"] == "Linux" and f["cpu"].lower() == "x86_64"
                                 and "linux-systemd" in f["file_name"]][0]
                linux_package_info = {
                    "file_name": linux_package["file_name"],
                    "url": linux_package["file_download_url"],
                    "md5": linux_package["checksum"]["md5sum"],
                    "sha256": linux_package["checksum"]["sha256sum"],
                    "sha512": linux_package["checksum"]["sha512sum"],
                }
                if this_branch_latest_meta["version"] is None:
                    this_branch_latest_meta["version"] = patch["release_id"]
                this_version_packages.append(linux_package_info)
                if len(this_version_packages) >= MAX_ALLOWED_VERSIONS:
                    break
            except IndexError:
                continue
        return_list.extend(this_version_packages)
        latest_meta.append(this_branch_latest_meta)
    for meta in latest_meta:
        logger.info(f"Latest MariaDB version for {meta['version_file_name']} is {meta['version']}")
    return return_list, latest_meta


if __name__ == "__main__":
    make_cache()
