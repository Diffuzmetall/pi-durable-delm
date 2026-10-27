# Происхождение

Это самостоятельная адаптация DeLM для Native Pi Durable, а не официальный пакет авторов исследования и не перенос Rust runtime продуктового плагина.

## Исследование

Mao, Yuzhen; Gu, Jerry; Chauhan, Aadi; Zhang, Qizheng; Kang, Hangoo; Mirhoseini, Azalia. **Decentralized Multi-Agent Systems with Shared Context**. Закреплённая версия: https://arxiv.org/abs/2606.10662v3 . Сайт авторов: https://yuzhenmao.github.io/DeLM/ . PDF/media в поставку не включены. Показатели ускорения из статьи не являются измерениями этого пакета.

## Исходный Python

https://github.com/yuzhenmao/DeLM, commit `66617616e708758f91624e5cc03659732b82f6a6`, MIT. Минимальный runtime-набор поставляется в `vendor/DeLM/`; полный license — `vendor/DeLM/LICENSE`. Его source paths и hashes зафиксированы в `provenance.json`. На исходной машине при начале переноса HEAD проверен на этот commit, checkout чистый. Это результат проверки source, не автоматическое доказательство переносимости новой сборки.

Включаем `board/shared_context.py`, ProtectedBoard, context_client и целый `runtime/containers.py` с package init files. Используется его HTTP handler; Docker/container helpers не запускаются при импорте и не становятся обязательной пользовательской зависимостью. Их ленивый `benchmark.task_compose` import требует исходного benchmark только при прямом вызове неиспользуемых Docker helpers; эта часть исследовательского runner не является публичной функцией нашего пакета. Сохраняется защита ProtectedBoard, а не незаметная подмена базовой доской.

Первичные формулировки кооперации и декомпозиции: `prompts/prompts_n2.py` и `prompts/prompts_n4.py` в указанном source commit. Ссылки: https://github.com/yuzhenmao/DeLM/blob/66617616e708758f91624e5cc03659732b82f6a6/prompts/prompts_n4.py . В standalone runtime они не обязательны; включение справочных копий отмечается отдельно, а не выдаётся за импортируемую зависимость.

## Продуктовый плагин — отдельный источник

https://github.com/Decentralized-LM/delm-agent-plugin . Исследованный архив: `0443e6fa05f6da36ef842cb8c36da9de69777073`; MIT, copyright DeLM contributors. Worker: https://github.com/Decentralized-LM/delm-agent-plugin/blob/0443e6fa05f6da36ef842cb8c36da9de69777073/plugin/worker.md . Отдельный закреплённый run skill: https://github.com/Decentralized-LM/delm-agent-plugin/blob/42fbfdc0d5b338170f9504e3a511772f2d15e675/skills/run/SKILL.md .

Его идеи explicit run identity, early useful output, ownership fencing, meaningful events и checkpoint recovery сопоставлены с нашей реализацией. Его private worktrees, macOS/server ownership, Codex hooks и Rust-команды не заявляются реализованными здесь. Rust runtime и архив плагина не поставляются; verbatim reference code при дополнительном включении требует полной license и отдельной записи manifest.

## Наши адаптации

Python domain/delivery/leases, read-only observer, Native integration, переносимый skill/launcher и packaging основаны на локальной адаптации delm-test. По явному решению владельца новые авторские части опубликованы под MIT в https://github.com/Diffuzmetall/pi-durable-delm ; полный текст — `LICENSE`. Это отдельное разрешение, не автоматическое наследование лицензии upstream. Production Native host gate остаётся открытым.

`provenance.json` различает unchanged/adapted/written-here и исходный hash от final artifact hash. `parity.json` связывает пользовательские функции с owning implementation и тестами. Незавершённая запись — явный pending, не ложный PASS.
