from pathlib import Path
from typing import Any, Callable

try:
    import ase.io
    import pandas
    import pymatgen.core
    import pymatgen.entries.computed_entries
    from pymatgen.entries.computed_entries import ComputedStructureEntry
except ImportError as exc:
    raise ImportError(
        "The parsers module requires the `ingest` extra of this package to be installed."
    ) from exc

from optimade.adapters import Structure
from optimade.models import EntryResource

from optimade_maker.config import PropertyDefinition


def load_csv_file(
    p: Path,
    properties: list[PropertyDefinition] | None = None,
) -> dict[str, dict[str, Any]]:
    """Parses a CSV file found at path `p` and returns a dictionary
    of properties keyed by ID.

    Will use the first column that contains the substring "id", which will
    be matched with the generated IDs.

    Parameters:
        p: Path to the CSV file.
        properties: List of property definitions to extract from the CSV file.

    Returns:
        A dictionary of ID -> properties.

    """
    df = pandas.read_csv(p)
    id_key = "id"
    if "id" not in df:
        id_keys = [f for f in df.columns if "id" in f.lower()]
        if not id_keys:
            raise RuntimeError(
                f"CSV file {p} must have a column containing 'id' : not just {df.columns}"
            )
        id_key = id_keys[0]

    # Copy found ID key and rename it to 'id'
    if id_key != "id":
        df["id"] = df[id_key]
    df = df.set_index("id")

    for prop in properties or []:
        # loop through any property aliases, saving the value if found and only checking
        # the real name if not
        for alias in prop.aliases or []:
            if alias in df:
                df[prop.name] = df[alias]
                break

    return df.to_dict(orient="index")


PROPERTY_PARSERS: dict[
    str, list[Callable[[Path, list[PropertyDefinition] | None], Any]]
] = {
    ".csv": [load_csv_file],
}

TYPE_MAP: dict[str | None, type] = {
    "float": float,
    "string": str,
    "integer": int,
    "boolean": bool,
}


def wrapped_json_parser(parser):
    """This wrapper allows `from_dict` parser functions to be called
    on a single JSON file.

    """

    def _wrapped_json_parser(path: Path) -> Any:
        import json

        with open(path) as f:
            data = json.load(f)

        entries = []
        # Either we already have a list of entries, or we need to find which key they are stored under
        if isinstance(data, list):
            for entry in data:
                entries.append(entry)

        elif isinstance(data, dict):
            for k in data:
                if isinstance(data[k], list):
                    for entry in data[k]:
                        entries.append(entry)

        for ind, e in enumerate(entries):
            try:
                entries[ind] = parser(e)
            except Exception as e:
                raise RuntimeError(f"Error parsing entry {entry} in {path}: {e}")

        return entries

    return _wrapped_json_parser


ENTRY_PARSERS: dict[str, list[Callable[[Path], Any]]] = {
    "structures": [
        ase.io.read,
        wrapped_json_parser(
            pymatgen.entries.computed_entries.ComputedStructureEntry.from_dict
        ),
        wrapped_json_parser(pymatgen.core.Structure.from_dict),
    ],
}


def parse_computed_structure_entry(
    pmg_entry: ComputedStructureEntry,
    properties: list[PropertyDefinition] | None = None,
) -> dict:
    """Convert a pymatgen ComputedStructureEntry to an OPTIMADE EntryResource."""

    entry = Structure.ingest_from(pmg_entry.structure).entry.dict()
    entry["attributes"].update(pmg_entry.data)
    entry["attributes"]["energy"] = pmg_entry.energy
    # try to find any unique ID fields and use it to overwrite the generated one
    for key in ("id", "mat_id", "task_id"):
        id = pmg_entry.data.get(key)
        if id:
            entry["id"] = id
            break

    for p in properties or []:
        # loop through any property aliases, saving the value if found and only checking
        # the real name if not
        for alias in p.aliases or []:
            if value := pmg_entry.data.get(alias) is not None:
                entry["attributes"][p.name] = value
                break
        else:
            entry["attributes"][p.name] = pmg_entry.data.get(p.name)

    return entry


def structure_ingest_wrapper(entry, properties=None):  # type: ignore
    return Structure.ingest_from(entry)


OPTIMADE_CONVERTERS: dict[
    str, list[Callable[[Any, list[PropertyDefinition] | None], EntryResource | dict]]
] = {
    "structures": [structure_ingest_wrapper, parse_computed_structure_entry],
}
