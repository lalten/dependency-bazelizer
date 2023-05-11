from typing import Final
from pathlib import Path
import logging
import subprocess

from src.module import (
    get_module_name,
    get_module_version,
)

logger = logging.getLogger(__name__)

# version attribute as listed in apt-cache show
VERSION_ATTRIBUTE: Final = "Version"
VERSION_DOT_TXT: Final = Path("version.txt")


def _extract_attribute(
    package_info: str, attribute: str, must_exist: bool = True
) -> str:
    "Extracts a specific attribute from the info listed using 'apt-cache' or 'dpkg-deb'."
    prefix = attribute + ": "
    lines = package_info.splitlines()

    for line in lines:
        line = line.lstrip()
        if line.startswith(attribute):
            return line[len(prefix) :]

    if not must_exist:
        return ""

    raise ValueError(
        f"{attribute} could not be extracted from package_info: {package_info}"
    )


def _get_deb_package_version_from_aptcache(name: str, arch: str) -> str:
    if not name or not arch:
        raise ValueError("both name and arch need to be provided")

    deb_package_name = f"{name}:{arch}"
    package_info = subprocess.check_output(
        ["apt-cache", "show", deb_package_name],
        encoding="utf-8",
        stderr=subprocess.STDOUT,
    )

    return _extract_attribute(package_info=package_info, attribute=VERSION_ATTRIBUTE)


def get_version_from_registry(
    registry_path: Path, name: str, arch: str, version: str = ""
) -> str:
    module_name = get_module_name(name=name, arch=arch)
    modules_path = registry_path / "modules"
    module_path = modules_path / module_name
    if not module_path.exists():
        logger.info(
            f"module {module_name} not found in local bazel registry, expected path: {module_path} does not exist."
        )

        return ""
    
    if version:
        return (
            version
            if Path.joinpath(module_path, get_module_version(version)).exists()
            else ""
        )

    versions = [
        version.name
        for version in Path.iterdir(module_path)
        if Path.is_dir(Path.joinpath(module_path, version))
    ]

    if not versions:
        raise ValueError(
            f"package: {get_module_name(name=name, arch=arch)}, exists in registry modules, but has no versions"
        )
    # TODO: improve version resolution algorithm
    versions.sort()

    version_output: str
    with open(
        Path(module_path, versions[-1], VERSION_DOT_TXT), "r", encoding='utf-8'
    ) as file:
        version_output = file.read()

    return version_output


def get_package_version(registry_path: Path, name: str, arch: str) -> str:
    dep_version = get_version_from_registry(registry_path=registry_path, name=name, arch=arch)
    if not dep_version:
        dep_version = _get_deb_package_version_from_aptcache(name, arch)

    return dep_version