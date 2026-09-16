# RepoGC scan report

**Reliability: RELIABLE**

## Metadata

- RepoGC version: `0.0.0`
- Report schema: `0.1`
- Generated at: `2026-09-02T07:41:02.702771+00:00`
- Commit: `67061a295a6f33f8f43e323c829640fd29ca651a`
- Branch: `main`
- Working tree dirty: `True`
- Scanner hash: `ca3270dc1784a6df009abcb3fb3a183ad4175c6d85103373233177d93869639a`
- Config hash: `65257d12a829245519469e4ec884c6a4f4f101811ed9672f56a0bae91489016e`
- AI annotation: `not_implemented`
- Scanned files: `19`

## Summary

- Broken references: 42
- Orphan candidates: 0
- Unimplemented markers: 23
- Duplicate candidates: 0

## Trend

- Baseline present: `True`
- New: 0
- Persistent: 65
- Resolved: 0
- Basis changed: `False`

> Findings are mechanical evidence and review candidates. They are not deletion verdicts.

## Findings

| ID | Category | Source | Target | Evidence | Line |
|---|---|---|---|---|---:|
| c03c4a8817ea4db9729995564820c163f20b5457 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/.gitlab-ci.yml | unresolved path: .gitlab-ci.yml | 14 |
| a725d5d13bb377047ee850642b7dd3864db5f005 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/SKILL.md | unresolved path: SKILL.md | 55 |
| 95f230f36b98a11d18051f25186b7f5db0d18e81 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/core_principles_memo.md | unresolved path: core_principles_memo.md | 21 |
| 67fb320528e8c62b1847ef9b08a926edb897e711 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/example.jsonl | unresolved path: example.jsonl | 37 |
| f3a19badf3d308cebfe7296acb580e9124cf98b3 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/process_log.md | unresolved path: process_log.md | 54 |
| 042cfa3d64fb408a7e50b2f028928d5ff4fa0839 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | docs/provenance_seal_mechanism.md | unresolved path: provenance_seal_mechanism.md | 21 |
| 33473aad88d02a4e1db03aac751d05b40a8d8345 | broken_reference | docs/HISTORICAL_REGRESSIONS.zh-CN.md | tools/guarded_push.py | unresolved path: tools/guarded_push.py | 11 |
| 87e3a01a06e564ec367bb5695bfa2ac8138ff5f0 | broken_reference | repogc.toml | AGENTS.md | unresolved path: AGENTS.md | 6 |
| bec9a9f4e406ad1324402a2a7e9cee38948b0561 | broken_reference | repogc.toml | CLAUDE.md | unresolved path: CLAUDE.md | 6 |
| 7006a2f2f65c916f44c3e63cd8c25994c7851267 | broken_reference | repogc.toml | CONTRIBUTING.md | unresolved path: CONTRIBUTING.md | 6 |
| 046fc589ac8860351b6e29ea0d5661a6f2394ea9 | broken_reference | repogc.toml | SECURITY.md | unresolved path: SECURITY.md | 6 |
| 9ae1ce3541ce60e7c563492b163e51960a53fe54 | broken_reference | src/repogc/config.py | src/repogc/AGENTS.md | unresolved path: AGENTS.md | 39 |
| 29ca7e34f707f608d42715acea335d6396cb1435 | broken_reference | src/repogc/config.py | src/repogc/CLAUDE.md | unresolved path: CLAUDE.md | 40 |
| c0ec91147391b54a0f6e2bf797645fc69aa2666c | broken_reference | src/repogc/config.py | src/repogc/CONTRIBUTING.md | unresolved path: CONTRIBUTING.md | 41 |
| a45cfdfebee5b6083d97d5f1ab100f4de1aa6a0a | broken_reference | src/repogc/config.py | src/repogc/SECURITY.md | unresolved path: SECURITY.md | 42 |
| ca34daaedbcbba0a99c03e25cea3e68caf59aecb | broken_reference | src/repogc/self_check.py | src/repogc/SKILL.md | unresolved path: SKILL.md | 40 |
| ce3e6e6f0b609e2d36f10367b2cdebe505e9c459 | broken_reference | src/repogc/self_check.py | src/repogc/core_principles_memo.md | unresolved path: core_principles_memo.md | 27 |
| 966bf670de830592213ba523079e62895999bfc3 | broken_reference | src/repogc/self_check.py | src/repogc/example.jsonl | unresolved path: example.jsonl | 44 |
| 69d4faf2eca11c36f214c7683c76ecfaa1d2fd01 | broken_reference | src/repogc/self_check.py | src/repogc/process_log.md | unresolved path: process_log.md | 61 |
| 3acfc0f87de7a6521d5de10dc6a725b4c83037ec | broken_reference | src/repogc/self_check.py | src/repogc/provenance_seal_mechanism.md | unresolved path: provenance_seal_mechanism.md | 27 |
| d3439dad18131099ceb08f958062f50fbfab6b51 | broken_reference | src/repogc/self_check.py | tools/guarded_push.py | unresolved path: tools/guarded_push.py | 19 |
| 0bcc0dc913997864cab482ccf5412dd9a3c77666 | broken_reference | tests/test_cli.py | reference/baseline.json | unresolved path: reference/baseline.json | 35 |
| c4443212ac8787de766adad7f36d8caee151b9ce | broken_reference | tests/test_cli.py | reports/latest.json | unresolved path: reports/latest.json | 34 |
| 67f67f7b336b4b2e26e9fa9c2c9a91c4acc25c66 | broken_reference | tests/test_cli.py | reports/latest.md | unresolved path: reports/latest.md | 33 |
| cdd9e53416cf46db27f69a9adfee569e08df65af | broken_reference | tests/test_cli.py | tests/baseline.json | unresolved path: baseline.json | 45 |
| ba8f2df78cf868ee82941d57ec29679b1ef45d97 | broken_reference | tests/test_cli.py | tests/latest.json | unresolved path: latest.json | 43 |
| dc30757192f17793696ea2ae61ea859f5debbb94 | broken_reference | tests/test_cli.py | tests/latest.md | unresolved path: latest.md | 42 |
| c433d5300acb5026f7cff5a3cf94da90c9153808 | broken_reference | tests/test_regressions.py | docs/live.md | unresolved path: docs/live.md | 129 |
| bfbe0065bb95813b9bee63723a694298f7ce251a | broken_reference | tests/test_regressions.py | outside.json | unresolved path: ../outside.json | 184 |
| b9030ff1f7aea2d74ef220d4239f4b6d647309f4 | broken_reference | tests/test_regressions.py | reports/generated.json | unresolved path: reports/generated.json | 244 |
| e2f0683efdf247e6f2da295f8c0a4aa85f2cc7e4 | broken_reference | tests/test_regressions.py | reports/phase0-bootstrap.md | unresolved path: reports/phase0-bootstrap.md | 269 |
| 1033c9638870f782da330e116c8c479a6d3a0a69 | broken_reference | tests/test_regressions.py | tests/SKILL.md | unresolved path: SKILL.md | 66 |
| cb76dcf82753f269e869e514d9978144b5a1f484 | broken_reference | tests/test_regressions.py | tests/core_principles_memo.md | unresolved path: core_principles_memo.md | 49 |
| 45b39896ac828ef31653ff5c6849b155fac9d642 | broken_reference | tests/test_regressions.py | tests/example.jsonl | unresolved path: example.jsonl | 88 |
| 944ea3e7e32c1b10d177c66e9644cbb0688bc88d | broken_reference | tests/test_regressions.py | tests/generated.json | unresolved path: generated.json | 248 |
| fe29240eeb1f762b1363a8db4bb7f2f024de5e11 | broken_reference | tests/test_regressions.py | tests/live.md | unresolved path: live.md | 131 |
| de3e09a47b8ce9a899452ca9d6f7f0bd799965e2 | broken_reference | tests/test_regressions.py | tests/notes.md | unresolved path: notes.md | 153 |
| f5f250577b5da6ed3a56c5ebb20bd1d99563579a | broken_reference | tests/test_regressions.py | tests/phase0-bootstrap.md | unresolved path: phase0-bootstrap.md | 273 |
| 2e58c84cac5c092141be47a606e41b1944c4eee5 | broken_reference | tests/test_regressions.py | tests/private-name.md | unresolved path: private-name.md | 234 |
| c57a19c469adcdce566c2a473ea98f83812cf261 | broken_reference | tests/test_regressions.py | tests/process_log.md | unresolved path: process_log.md | 110 |
| 262ed96895109bb1bce75d67e8ed00ce94e72192 | broken_reference | tests/test_regressions.py | tests/provenance_seal_mechanism.md | unresolved path: provenance_seal_mechanism.md | 49 |
| 113811a46d5fbca1872686516e86aba39e3849e3 | broken_reference | tests/test_regressions.py | tools/guarded_push.py | unresolved path: tools/guarded_push.py | 43 |
| 951beb855aaf34079aadd03a16f872b5163e6795 | unimplemented_marker | docs/GC_MANUAL.zh-CN.md | — | 3. `unimplemented_marker`:配置词表命中未实现标记。 | 82 |
| 3c0ef87431da365f3747d547acd289c2c2c5b38f | unimplemented_marker | docs/GC_MANUAL.zh-CN.md | — | Markdown 在当前扫描面没有入站引用、哪些承诺仍有未实现标记、哪些文档 | 14 |
| 9eb53269461f91473836818a82da01b06c7ad50f | unimplemented_marker | docs/PHASE0_STATUS.zh-CN.md | — | ## 尚未实现或验证 | 50 |
| 0911355fdfb9136781290bc9a36e116bab07039f | unimplemented_marker | docs/PHASE0_STATUS.zh-CN.md | — | - 四类机械扫描:unresolved reference、orphan candidate、未实现标记、重复候选; | 38 |
| 852fddd3f1ad0065cbe979b1b852f4c37efc9ba9 | unimplemented_marker | docs/PHASE0_STATUS.zh-CN.md | — | - 未实现词表中含中英文项目词汇; | 93 |
| fdb90c94a75adb652e3e04f91c743e4a1d49e701 | unimplemented_marker | repogc.toml | — | tokens = ["TODO", "FIXME", "XXX", "NOT_IMPLEMENTED", "未实现", "待实现"] | 13 |
| e2d068a575f490bbfabd9c234ecc67cc066be948 | unimplemented_marker | src/repogc/config.py | — | "FIXME", | 50 |
| 80498f8b8d2f9ad9d96a9a0849e0205235175990 | unimplemented_marker | src/repogc/config.py | — | "NOT_IMPLEMENTED", | 52 |
| ba50d955dfb33cad00bcef6965ec491d2cfe2923 | unimplemented_marker | src/repogc/config.py | — | "TODO", | 49 |
| 1448ca5ad970395ee0c76026ee2269a7d408833f | unimplemented_marker | src/repogc/config.py | — | "XXX", | 51 |
| e1d82f7950a3d8c5176eddfde978ea8a480d719b | unimplemented_marker | src/repogc/config.py | — | "待实现", | 54 |
| 0a55a1f27ccd5be26a98ce1c7ea6b3853ca088fd | unimplemented_marker | src/repogc/config.py | — | "未实现", | 53 |
| 843a9ce5ac636fe45f02dd53569083f78f51d86c | unimplemented_marker | src/repogc/models.py | — | "ai_annotation_status": "not_implemented", | 42 |
| 64643706e7bd3113fe2fb31f9ce094ca8f742dcf | unimplemented_marker | src/repogc/reporting.py | — | "ai_annotation_status": "not_implemented", | 22 |
| 374df4157580f478557c4d57f377b94954c0c160 | unimplemented_marker | src/repogc/self_check.py | — | after = stable_id("SKILL.md", "TODO preserve this contract") | 41 |
| bb2f0312c06337d71ab7bcaf0da5254ac01d8c45 | unimplemented_marker | src/repogc/self_check.py | — | before = stable_id("SKILL.md", "TODO preserve this contract") | 40 |
| d4dd6b5017431e5031f015db684d1e67217cf759 | unimplemented_marker | tests/test_cli.py | — | (root / "README.md").write_text("TODO explain behavior\n", encoding="utf-8") | 15 |
| 071d1899af74085390ecccb66d77ebb11189f551 | unimplemented_marker | tests/test_cli.py | — | tokens = ["TODO"] | 30 |
| 78702024a0cda0b1d1227b1248b2ea45d8b8d0ab | unimplemented_marker | tests/test_regressions.py | — | "Inserted context\n# Contract\nTODO preserve this contract\n", | 76 |
| 3ec9e8d42b8c05b844cb3826884236c067aae208 | unimplemented_marker | tests/test_regressions.py | — | "marker_tokens": ("TODO",), | 32 |
| 809537538a6d5073eafc4286c4b539f3e061606f | unimplemented_marker | tests/test_regressions.py | — | (root / "README.md").write_text("TODO test\n", encoding="utf-8") | 189 |
| 5438434d08c173944cb45bfa121de233cac730a5 | unimplemented_marker | tests/test_regressions.py | — | (root / "docs" / "live.md").write_text("TODO document behavior\n", encoding="utf-8") | 131 |
| 02134b2d6c8c124e4d6f033f72326c53aff0cd92 | unimplemented_marker | tests/test_regressions.py | — | skill.write_text("# Contract\nTODO preserve this contract\n", encoding="utf-8") | 67 |

## Known limits

This static scan may not observe dynamic, external, human-only, contract, or process consumers.
Review all liveness dimensions before changing any reported artifact.
