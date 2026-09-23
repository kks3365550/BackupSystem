# File Contract Summary: `core/filter.py`
- **Lines**: 189
- **Symbols Count**: 6
- **Imports Count**: 5

### Key Dependencies (Imports)
`fnmatch`, `os`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`PathFilter`** | `global` | L107-L188 |  |
| `method` | **`__init__`** | `PathFilter` | L108-L136 | args: (self, exclude_patterns, include_patterns, use_defaults: bool) |
| `function` | **`_matches_common`** | `PathFilter` | L138-L148 | args: (self, name_lower: str) -> bool /* Helper to match exact names, substrings, */ |
| `function` | **`is_dir_excluded`** | `PathFilter` | L150-L155 | args: (self, dirname: str) -> bool /* Fast O(1) check for directory exclusion  */ |
| `function` | **`is_file_excluded`** | `PathFilter` | L157-L163 | args: (self, filename: str) -> bool /* Fast O(1) check for file exclusion. */ |
| `function` | **`is_excluded`** | `PathFilter` | L165-L188 | args: (self, path: str, is_dir: bool) -> bool |

