# Third-party notices

## DeLM Python runtime

Source: https://github.com/yuzhenmao/DeLM/tree/66617616e708758f91624e5cc03659732b82f6a6 . License: MIT. Full original notice and permission text are supplied verbatim in `vendor/DeLM/LICENSE`; that text, including its original years and author names, must remain with included copies/substantial portions. File-level paths/hashes and adaptation status are in `provenance.json`.

The following source files are planned/included unchanged under that license: board/__init__.py, board/shared_context.py, board/protected_board.py, board/context_client.py, runtime/__init__.py, runtime/containers.py. Whether each file is already materialized is explicit in the final source map, not inferred from this notice.

## Research citation and product-plugin reference

Paper/site/repository references are documented in `UPSTREAM.md`. No paper PDF, image, video, screenshot or research archive is included. The MIT product-plugin archive is a distinct reference, not a bundled runtime; its code/license must be mapped separately if a later producer includes any verbatim portion.

## Native SDK / platform

The extension uses the user's separately installed Native SDK. The minimal public API patch in `extensions/delm/public-host-api.patch` contains source context derived from public Pi v1.0.2, commit `cd32f7725fdbddbaecdff5b1e68491563394e0ca`: https://github.com/earendil-works/pi/tree/cd32f7725fdbddbaecdff5b1e68491563394e0ca . That source is MIT, Copyright (c) 2025 Mario Zechner; its full original notice and permission text are included verbatim in `LICENSES/pi-native.txt`. No complete platform host, private controller, provider credentials or author installation is bundled. The patch is an explicit compatibility requirement, not a claim that an unpatched host already exposes the new API. Actual required versions, local-only capability and retained guards must be verified in `docs/native-compatibility.md`; no hidden author environment or fake production admission is permitted.

## Local adaptation: MIT by owner authorization

The owner explicitly authorized publication of the adapter, packaging and skill changes under MIT in https://github.com/Diffuzmetall/pi-durable-delm . The full license for these parts is in `LICENSE`. This is a separate owner decision, not an automatic grant from the upstream MIT notice. The original upstream copyright and full license remain unchanged in `vendor/DeLM/LICENSE`. Public source availability does not establish production Native host compatibility or npm publication.
