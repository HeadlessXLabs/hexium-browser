# Persona networks

Runtime loads the packed `*.zip` files next to this folder’s parent (`src/hexium_browser/persona/data/`). Unpacked JSON is optional: extract a zip’s `network.json` only when editing, then `python scripts/upgrade_persona_datapack.py`.

| Zip | Role |
| --- | --- |
| `fingerprint-network-definition.zip` | Joint OS/GPU/screen/UA |
| `header-network-definition.zip` | HTTP header tokens |
| `input-network-definition.zip` | Header input net |

Also: `headers-order.json`, `browser-helper-file.json`.

These are **Bayesian networks** (`possibleValues` + `conditionalProbabilities`). New Chrome versions must be cloned as CPT keys, not pasted as a list.

Sampler rewrites the drawn UA + UA-CH together to Hexium’s engine pin `151.0.7922.174` at launch.
