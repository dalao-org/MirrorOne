from typing import Tuple, List, Dict, Any


def make_cache() -> tuple[list[dict[str, str | Any]], list[dict[str, str]]]:
    resource_list = []
    latest_meta = [
        {"version_file_name": "pcre_ver", "version": "8.45"},
        {"version_file_name": "libmcrypt_ver", "version": "2.5.8"},
        {"version_file_name": "mcrypt_ver", "version": "2.6.8"},
        {"version_file_name": "mhash_ver", "version": "0.9.9.9"},
    ]

    url_list = ["https://www.sourceguardian.com/loaders/download/loaders.linux-x86_64.tar.gz",
                "https://www.sourceguardian.com/loaders/download/loaders.linux-armhf.tar.gz",
                "https://www.sourceguardian.com/loaders/download/loaders.linux-aarch64.tar.gz",
                "https://github.com/kmvan/x-prober/releases/latest/download/prober.php",
                # Ocp is no longer maintained
                "https://gist.githubusercontent.com/ck-on/4959032/raw/ocp.php",
                # Ioncube provides official direct download link for the latest version
                "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz",
                "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86.tar.gz",
                "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_aarch64.tar.gz",
                "https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_armv7l.tar.gz",
                # pcre is discontinued; pcre2 is the successor
                "https://versaweb.dl.sourceforge.net/project/pcre/pcre/8.45/pcre-8.45.tar.gz",
                # libmemcached last update in 2014
                "https://launchpad.net/libmemcached/1.0/1.0.18/+download/libmemcached-1.0.18.tar.gz",
                # libmcrypt last update in 2015
                "https://src.fedoraproject.org/repo/pkgs/libmcrypt/libmcrypt-2.5.8.tar.gz/0821830d930a86a5c69110837c55b7da/libmcrypt-2.5.8.tar.gz",
                # mcrypt last update in 2015
                "https://src.fedoraproject.org/repo/pkgs/mcrypt/mcrypt-2.6.8.tar.gz/97639f8821b10f80943fa17da302607e/mcrypt-2.6.8.tar.gz",
                # mhash last update in 2009; file type changed from tar.gz to tar.bz2 !!!
                "https://src.fedoraproject.org/repo/pkgs/mhash/mhash-0.9.9.9.tar.bz2/md5/f91c74f9ccab2b574a98be5bc31eb280/mhash-0.9.9.9.tar.bz2",
                # ez_setup.py is maintained officially
                "https://bootstrap.pypa.io/ez_setup.py",
                # start-stop-daemon.c last update in 2017
                "https://raw.githubusercontent.com/daleobrien/start-stop-daemon/master/start-stop-daemon.c",
                # eaccelerator last update in 2010
                "https://src.fedoraproject.org/repo/pkgs/php-eaccelerator/eaccelerator-0.9.6.1.tar.bz2/32ccd838e06ef5613c2610c1c65ed228/eaccelerator-0.9.6.1.tar.bz2",
                # mod_remoteip.c last update in 2016
                "https://opensource.apple.com/source/apache/apache-795.1/httpd/modules/metadata/mod_remoteip.c"]
    for url in url_list:
        resource_list.append({
            "url": url,
            "file_name": url.split("/")[-1]
        })
    return resource_list, latest_meta
