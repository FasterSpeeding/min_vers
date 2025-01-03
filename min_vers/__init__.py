# BSD 3-Clause License
#
# Copyright (c) 2022-2025, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Temporary description."""
from __future__ import annotations

import abc
import typing

import packaging.requirements
import pkginfo  # pyright: ignore[reportMissingTypeStubs]

if typing.TYPE_CHECKING:
    import pathlib
    from collections import abc as collections
    from typing import Self

    import shippinglabel.requirements


class _Extractor(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def dependencies(self) -> collections.Sequence[packaging.requirements.Requirement]: ...

    @abc.abstractmethod
    def optional_dependencies(
        self,
    ) -> collections.Mapping[str, collections.Sequence[packaging.requirements.Requirement]]: ...


class _PyProjectExtractor(_Extractor):  # pyright: ignore [reportUnusedClass]
    __slots__ = ("_pyproject",)

    def __init__(self, path: pathlib.Path, /) -> None:
        import pyproject_parser

        self._pyproject: pyproject_parser.PyProject = pyproject_parser.PyProject.load(str(path.absolute()))

    def dependencies(self) -> list[shippinglabel.requirements.ComparableRequirement]:
        if self._pyproject.project:
            return self._pyproject.project["dependencies"]

        return []

    def optional_dependencies(self) -> dict[str, list[shippinglabel.requirements.ComparableRequirement]]:
        if self._pyproject.project:
            return self._pyproject.project["optional-dependencies"]

        return {}


class _PkgExtractor(_Extractor):  # pyright: ignore [reportUnusedClass]
    __slots__ = ("_dependencies", "_optional_dependencies")

    def __init__(self, distribution: pkginfo.Distribution, /) -> None:
        self._dependencies: list[packaging.requirements.Requirement] = []
        self._optional_dependencies: dict[str, list[packaging.requirements.Requirement]] = {}

        for constraint in map(packaging.requirements.Requirement, distribution.requires_dist):
            if not constraint.extras:
                self._dependencies.append(constraint)
                continue

            extras = constraint.extras
            constraint.extras = set()
            for extra in extras:
                try:
                    self._optional_dependencies[extra].append(constraint)

                except KeyError:
                    self._optional_dependencies[extra] = [constraint]

    @classmethod
    def from_installed(cls, path: str, /) -> Self:
        package = pkginfo.Installed(path)
        if package.package is None:
            error_message = f"{path!r} is not installed"
            raise ModuleNotFoundError(error_message)

        return cls(package)

    @classmethod
    def from_sdist(cls, path: pathlib.Path, /) -> Self:
        return cls(pkginfo.SDist(path))

    @classmethod
    def from_wheel(cls, path: pathlib.Path, /) -> Self:
        return cls(pkginfo.Wheel(path))

    def dependencies(self) -> list[packaging.requirements.Requirement]:
        return self._dependencies

    def optional_dependencies(self) -> dict[str, list[packaging.requirements.Requirement]]:
        return self._optional_dependencies


class _RequirementsExtractor(_Extractor):  # pyright: ignore [reportUnusedClass]
    __slots__ = ("_dependencies",)

    def __init__(self, *paths: pathlib.Path) -> None:
        import requirements

        self._dependencies: dict[str, list[packaging.requirements.Requirement]] = {}
        for path in paths:
            with path.open("r") as file:
                name = path.name.rsplit(".", 1)[0]
                self._dependencies[name] = [
                    packaging.requirements.Requirement(req.line) for req in requirements.parse(file)
                ]

    def dependencies(self) -> list[packaging.requirements.Requirement]:
        return []

    def optional_dependencies(self) -> dict[str, list[packaging.requirements.Requirement]]:
        return self._dependencies
