<div align="center" style="padding: 2em;">
<span style="padding: 1em">
<img height="70px" align="center" src="https://matsci.org/uploads/default/original/2X/b/bd2f59b3bf14fb046b74538750699d7da4c19ac1.svg">
</span>
</div>

# <div align="center">optimade-maker</div>

<div align="center">

[![PyPI - Version](https://img.shields.io/pypi/v/optimade-maker?color=4CC61E)](https://pypi.org/project/optimade-maker/)
![PyPI - License](https://img.shields.io/pypi/l/optimade-maker?color=blue)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/materialscloud-org/optimade-maker/ci.yml)

</div>

Tools for making [OPTIMADE APIs](https://optimade.org) from various formats of structural data (e.g. an archive of CIF files).

This repository contains the `src/optimade-maker` Python package and the corresponding CLI tool `optimake` that work towards this aim. Features include

- definition of a config file format (`optimade.yaml`) for annotating data archives to be used in the OPTIMADE ecosystem;
- conversion of the raw data into corresponding OPTIMADE types using pre-existing parsers (e.g., ASE for structures);
- conversion of the annotated data archive into an intermediate JSONLines file format that can be ingested into a database and used to serve a full OPTIMADE API.
- serving either an annotated data archive or a JSONLines file as an OPTIMADE API (using the [`optimade-python-tools`](https://github.com/Materials-Consortia/optimade-python-tools/)
  reference server implementation).

## Usage

See `./examples` for a more complete set of supported formats and corresponding `optimade.yaml` config files.

### Annotating with `optimade.yaml`

To annotate your structural data for `optimade-maker`, the data archive needs to be accompanied by an `optimade.yaml` config file. The following is a simple example for a zip archive (`structures.zip`) of cif files together with an optional property file (`data.csv`):

```yaml
config_version: 0.1.0
database_description: Simple database

entries:
  - entry_type: structures
    entry_paths:
      - file: structures.zip
        matches:
          - cifs/*/*.cif
    # (optional) property file and definitions:
    property_paths:
      - file: data.csv
    property_definitions:
      - name: energy
        title: Total energy per atom
        description: The total energy per atom as computed by DFT
        unit: eV/atom
        type: float
```

### Structure `id`s and property files

`optimade-maker` will assign an `id` for each structure based on its full path in the archive, following a simple deterministic rule: from the set of all archive paths, the maximum common path prefix and postfix (including file extensions) are removed. E.g.

```
structures.zip/cifs/set1/101.cif
structures.zip/cifs/set2/102.cif
```

produces `["set1/101", "set2/102"]`.

The property files need to either refer to these `id`s or the full path in the archive to be associated with a structure. E.g. a possible property `csv` file could be

```csv
id,energy
set1/101,2.5
structures.zip/cifs/set2/102.cif,3.2
```

### Installing and running `optimake`

Install with

```bash
pip install optimade-maker
```

this will also make the `optimake` CLI utility available.

For a folder containing the data archive and the `optimade.yaml` file (such as in `/examples`), run

- `optimake convert .` to just convert the entry into the JSONL format (see below).
- `optimake serve .` to start the OPTIMADE API (this also first converts the entry, if needed);

For more detailed information see also `optimake --help`.

## `optimade-maker` JSONLines Format

As described above, `optimade-maker` works via an intermediate JSONLines file representation of an OPTIMADE API (see also the [corresponding issue in the specification](https://github.com/Materials-Consortia/OPTIMADE/issues/471)).
This file should provide enough metadata to spin up an OPTIMADE API with many different entry types.
The format is as follows:

- First line must be a dictionary with the key `x-optimade`, containing a sub-dictionary of metadata (such as the OPTIMADE API version).
- Second line contains the `info/structures` endpoint.
- Third line contains the `info/references` endpoint, if present.
- Then each line contains an entry from the corresponding individual structure/reference endpoints.

```json
{"x-optimade": {"meta": {"api_version": "1.1.0"}}}
{"type": "info", "id": "structures", "properties": {...}}
{"type": "info", "id": "references", "properties": {...}}
{"type": "structures", "id": "1234", "attributes": {...}}
{"type": "structures", "id": "1235", "attributes": {...}}
{"type": "references", "id": "sfdas", "attributes": {...}}
```

NOTE: the `info/` endpoints in [OPTIMADE v1.2.0](https://www.optimade.org/specification/#entry-listing-info-endpoints) will include `type` and `id` as well.

## Relevant links

- [Roadmap and meeting notes](https://docs.google.com/document/d/1cIpwuX6Ty5d3ZHKYWktQaBBQcI9fYmgG_hsD1P1UpO4/edit)
- [OPTIMADE serialization format notes](https://docs.google.com/document/d/1vf8_qxSRP5lCSb0P3M9gTr6nqkERxgOoSDno6YLcCjo/edit)
- [Flow diagram](https://excalidraw.com/#json=MBNl66sARCQekVrKZXDg8,K35f5FwmiS46vlsYGMJdrw)

## Contributors

Initial prototype was created at the Paul Scherrer Institute, Switzerland in the week of
12th-16th June 2023.

Authors (alphabetical):

- Kristjan Eimre
- Matthew Evans
- Giovanni Pizzi
- Gian-Marco Rignanese
- Jusong Yu
- Xing Wang
