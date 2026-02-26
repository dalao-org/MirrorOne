"""
Miscellaneous static-URL resources scraper.
Handles fixed/versioned resources that don't need dynamic discovery:
  SourceGuardian loaders, IonCube loaders, x-prober, ocp.php,
  pcre, libmemcached, libmcrypt, mcrypt, mhash, ez_setup.py,
  start-stop-daemon.c, eaccelerator, mod_remoteip.c
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


# Static URLs that are simply mirrored as-is.
# Entries: (url, file_name, version)
# - version="latest"  → always-overwritten single slot (loaders, scripts)
# - explicit version  → pinned, rarely changes
_STATIC_RESOURCES: list[tuple[str, str, str]] = [
    # SourceGuardian loaders (official rolling "latest" download links)
    (
        "https://www.sourceguardian.com/loaders/download/loaders.linux-x86_64.tar.gz",
        "loaders.linux-x86_64.tar.gz",
        "latest",
    ),
    (
        "https://www.sourceguardian.com/loaders/download/loaders.linux-armhf.tar.gz",
        "loaders.linux-armhf.tar.gz",
        "latest",
    ),
    (
        "https://www.sourceguardian.com/loaders/download/loaders.linux-aarch64.tar.gz",
        "loaders.linux-aarch64.tar.gz",
        "latest",
    ),
    # x-prober (official latest release redirect)
    (
        "https://github.com/kmvan/x-prober/releases/latest/download/prober.php",
        "prober.php",
        "latest",
    ),
    # ocp.php (no longer maintained; pinned gist)
    (
        "https://gist.githubusercontent.com/ck-on/4959032/raw/ocp.php",
        "ocp.php",
        "latest",
    ),
    # IonCube loaders (official rolling download links)
    (
        "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz",
        "ioncube_loaders_lin_x86-64.tar.gz",
        "latest",
    ),
    (
        "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86.tar.gz",
        "ioncube_loaders_lin_x86.tar.gz",
        "latest",
    ),
    (
        "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_aarch64.tar.gz",
        "ioncube_loaders_lin_aarch64.tar.gz",
        "latest",
    ),
    (
        "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_armv7l.tar.gz",
        "ioncube_loaders_lin_armv7l.tar.gz",
        "latest",
    ),
    # pcre (discontinued; pcre2 is the successor — pinned at final release 8.45)
    (
        "https://versaweb.dl.sourceforge.net/project/pcre/pcre/8.45/pcre-8.45.tar.gz",
        "pcre-8.45.tar.gz",
        "8.45",
    ),
    # libmemcached (last updated 2014; pinned)
    (
        "https://launchpad.net/libmemcached/1.0/1.0.18/+download/libmemcached-1.0.18.tar.gz",
        "libmemcached-1.0.18.tar.gz",
        "1.0.18",
    ),
    # libmcrypt (last updated 2015; pinned via Fedora pkgs mirror)
    (
        "https://src.fedoraproject.org/repo/pkgs/libmcrypt/libmcrypt-2.5.8.tar.gz"
        "/0821830d930a86a5c69110837c55b7da/libmcrypt-2.5.8.tar.gz",
        "libmcrypt-2.5.8.tar.gz",
        "2.5.8",
    ),
    # mcrypt (last updated 2015; pinned via Fedora pkgs mirror)
    (
        "https://src.fedoraproject.org/repo/pkgs/mcrypt/mcrypt-2.6.8.tar.gz"
        "/97639f8821b10f80943fa17da302607e/mcrypt-2.6.8.tar.gz",
        "mcrypt-2.6.8.tar.gz",
        "2.6.8",
    ),
    # mhash (last updated 2009; pinned via Fedora pkgs mirror — note: .tar.bz2)
    (
        "https://src.fedoraproject.org/repo/pkgs/mhash/mhash-0.9.9.9.tar.bz2"
        "/md5/f91c74f9ccab2b574a98be5bc31eb280/mhash-0.9.9.9.tar.bz2",
        "mhash-0.9.9.9.tar.bz2",
        "0.9.9.9",
    ),
    # ez_setup.py (maintained by PyPA)
    (
        "https://bootstrap.pypa.io/ez_setup.py",
        "ez_setup.py",
        "latest",
    ),
    # start-stop-daemon.c (last updated 2017; pinned GitHub raw)
    (
        "https://raw.githubusercontent.com/daleobrien/start-stop-daemon/master/start-stop-daemon.c",
        "start-stop-daemon.c",
        "latest",
    ),
    # eaccelerator (last updated 2010; pinned via Fedora pkgs mirror)
    (
        "https://src.fedoraproject.org/repo/pkgs/php-eaccelerator"
        "/eaccelerator-0.9.6.1.tar.bz2"
        "/32ccd838e06ef5613c2610c1c65ed228/eaccelerator-0.9.6.1.tar.bz2",
        "eaccelerator-0.9.6.1.tar.bz2",
        "0.9.6.1",
    ),
    # mod_remoteip.c (last updated 2016; pinned Apple opensource mirror)
    (
        "https://opensource.apple.com/source/apache/apache-795.1/httpd/modules/metadata/mod_remoteip.c",
        "mod_remoteip.c",
        "latest",
    ),
]

# Pinned version metadata entries (used by suggest_versions.txt)
_VERSION_METAS: list[tuple[str, str]] = [
    ("pcre_ver", "8.45"),
    ("libmcrypt_ver", "2.5.8"),
    ("mcrypt_ver", "2.6.8"),
    ("mhash_ver", "0.9.9.9"),
]


@registry.register("misc")
class MiscScraper(BaseScraper):
    """Scraper for miscellaneous static/pinned resources."""

    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)

        for url, file_name, version in _STATIC_RESOURCES:
            result.resources.append(Resource(
                file_name=file_name,
                url=url,
                version=version,
            ))

        for key, version in _VERSION_METAS:
            result.version_metas.append(VersionMeta(key=key, version=version))

        result.success = True
        return result
