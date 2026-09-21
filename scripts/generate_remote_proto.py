from pathlib import Path

import grpc_tools
from grpc_tools import protoc

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTO_ROOT = REPOSITORY_ROOT / "proto"
GENERATED_ROOT = REPOSITORY_ROOT / "src" / "bluesec1_client" / "proto"
PROTO_FILE = PROTO_ROOT / "investigation" / "runtime" / "v1" / "runtime.proto"
WELL_KNOWN_PROTO_ROOT = Path(grpc_tools.__file__).resolve().parent / "_proto"
GENERATED_MESSAGE_FILE = GENERATED_ROOT / "investigation" / "runtime" / "v1" / "runtime_pb2.py"
GENERATED_GRPC_FILE = GENERATED_ROOT / "investigation" / "runtime" / "v1" / "runtime_pb2_grpc.py"


def _create_package_markers() -> None:
    """Create importable package directories around generated modules."""
    package_directory = GENERATED_ROOT
    for package_part in (None, "investigation", "runtime", "v1"):
        if package_part is not None:
            package_directory /= package_part
        package_directory.mkdir(parents=True, exist_ok=True)
        (package_directory / "__init__.py").touch(exist_ok=True)


def _replace_generated_absolute_import() -> None:
    """Make the generated gRPC module import its sibling message module."""
    absolute_import = (
        "from investigation.runtime.v1 import runtime_pb2 as "
        "investigation_dot_runtime_dot_v1_dot_runtime__pb2"
    )
    relative_import = (
        "from . import runtime_pb2 as investigation_dot_runtime_dot_v1_dot_runtime__pb2"
    )
    generated_source = GENERATED_GRPC_FILE.read_text(encoding="utf-8")
    if absolute_import not in generated_source and relative_import not in generated_source:
        raise RuntimeError("generated gRPC import has an unexpected form")
    GENERATED_GRPC_FILE.write_text(
        generated_source.replace(absolute_import, relative_import),
        encoding="utf-8",
    )


def _ensure_well_known_dependency_import() -> None:
    """Load the imported Struct descriptor before registering the runtime descriptor."""
    dependency_import = (
        "from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2"
    )
    insertion_point = "# @@protoc_insertion_point(imports)"
    generated_source = GENERATED_MESSAGE_FILE.read_text(encoding="utf-8")
    if dependency_import in generated_source:
        return
    if insertion_point not in generated_source:
        raise RuntimeError("generated message import insertion point is missing")
    GENERATED_MESSAGE_FILE.write_text(
        generated_source.replace(
            insertion_point,
            f"{dependency_import}\n\n{insertion_point}",
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Generate committed Python messages, type hints, and gRPC stubs."""
    _create_package_markers()
    exit_code = protoc.main(
        [
            "grpc_tools.protoc",
            f"--proto_path={PROTO_ROOT}",
            f"--proto_path={WELL_KNOWN_PROTO_ROOT}",
            f"--python_out={GENERATED_ROOT}",
            f"--pyi_out={GENERATED_ROOT}",
            f"--grpc_python_out={GENERATED_ROOT}",
            str(PROTO_FILE),
        ]
    )
    if exit_code != 0:
        raise RuntimeError(f"Protobuf generation failed with exit code {exit_code}")
    _ensure_well_known_dependency_import()
    _replace_generated_absolute_import()


if __name__ == "__main__":
    main()
