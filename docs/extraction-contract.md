# Контракт автономной локальной поставки

> Исторический контракт переноса. Последующее прямое поручение владельца разрешает MIT, Git init, commit, создание публичного `Diffuzmetall/pi-durable-delm` и push. Ограничение на публикацию исходников ниже этим решением снято; production Native gate, запрет экспорта приватных данных и ограничения на npm/release остаются.

Исполняется прямое поручение пользователя `docs/DeLM-crew-extraction-prompt.md` исходного проекта. SOURCE — исходный delm-test; TARGET — новый отдельный `pi-durable-delm`. В публичном runtime не должно быть абсолютных путей SOURCE/домашнего стенда. Текущая команда и её DeLM-доска только координируют перенос: не создавать новые conversations, модели, servers или trackers. Исходные product/skill/host/upstream/run-файлы read-only; только операторское kickoff-сообщение существующим Tern panes отдельно разрешено пользователем.

## Ранние интерфейсы и scopes

- Alice: `scripts/delm_*.py`, `vendor/DeLM/`, `prompts/`, `examples/`, `tests/test_*.py`; root packaging (`package.json`, `bin/`, `packaging/`, `tests/packaging/`) после согласования Native manifest. Также `UPSTREAM.md`, `THIRD_PARTY_NOTICES.md`, `provenance.json`, `parity.json`, этот контракт.
- Bob: `extensions/delm/`, **пять scoped `tests/delm-*.test.mjs` в корне tests**, `docs/native-compatibility.md`. Публичный admission/SDK gate исследуется сразу. Не редактировать package.json: передать требуемый manifest/API Alice.
- Carol: `skills/delm/`, `tests/launcher/`. Использовать штатный createskill workflow для экспортируемого навыка; установленный `_DELM` не менять, приватный Config.json не копировать. Skill Paths получают корень из установленного пакета, а не LIFEOS или SOURCE.
- Dave: README, docs (кроме этого контракта и `native-compatibility.md`), `tests/acceptance/`, `release-readiness.md`; независимая приёмка только конечного артефакта. Alice передаёт provenance/notice final review в PUB-08 последовательно.

Уточнение путей тестов относительно первоначальных task details: **сохраняем исходную плоскую tests/** для Python и пяти Node files, чтобы не ломать проверенное относительное расположение imports. Расширения `test_*.py` и `delm-*.test.mjs` разделяют владельцев. Новые launcher/packaging/acceptance tests — в своих подкаталогах. Никакого historical DCG glob.

Команды проверок запускаются с cwd TARGET. Существующие native conversations остаются привязанными к исходному workspace/run; не менять их cwd/session или frozen START/WORKER. Source-board leases не могут резервировать внешний TARGET: boundary advisory остаётся честной, безопасность параллельных target writes обеспечивается disjoint claim scopes и явным handoff, не обходом нормализации lease.

## Python и минимальный upstream

Сохраняются рабочие entrypoints `python3 scripts/delm_local.py init/serve/context/worker` и `python3 scripts/delm_board.py RUN --observe`, actor-local executable, все публичные legacy/domain операции и isolated/shared режимы.

Vendored runtime: `vendor/DeLM/board/{__init__.py,shared_context.py,protected_board.py,context_client.py}`, `vendor/DeLM/runtime/{__init__.py,containers.py}`, `vendor/DeLM/LICENSE`. Все эти файлы сначала включаются **побайтно без изменений** из upstream commit `66617616e708758f91624e5cc03659732b82f6a6`. Импорт `containers.py` и используемый `handler` требуют только stdlib и BoardError/OriginalReadError: импорт не устанавливает/не запускает Docker. Сохранённые, но не вызываемые нашим адаптером Docker helpers содержат ленивый `benchmark.task_compose` import; они не являются поддерживаемым CLI продукта и не входят в его исполняемое import closure. Сохраняем целый небольшой файл вместо незаметно урезанного «оригинала». Транзитивных сторонних Python dependencies в этом замыкании нет.

Наш `delm_local.py` должен находить upstream относительно installed package root (`vendor/DeLM`), не SOURCE. Инициализация генерирует scripts/extension/template bindings относительно своего installed root. Остальные модули сохраняют события, тела вложений в attached DB, транзакции, actor auth, exact request replay, generation fencing, completion-cycle проверку deps+outputs, snapshots/pending/read→ACK, leases и observer. Нельзя упростить до SharedContext вместо ProtectedBoard.

Минимальный demo `examples/slugify` и Python tests переносятся без реальных run/credentials. Свежий temporary demo run — вне demo workspace; никакой установки новых пакетов или запуска реальных моделей.

## Native/public capability gate

Bob сверяет целевой установленный SDK и публичный package/extension механизм по документации и действующему API. `createDelmWait({run,actor,admitInput})` может остаться тестируемой фабрикой, но production install обязан получать admission из доказанного публичного доверенного механизма. Текущее получение через HINDSIGHT_CONTROLLER — **не публичный контракт по умолчанию**. Нельзя публиковать hidden private dependency, allow-all fallback, FauxHost как production или копию Native host.

При отсутствии публичной capability Bob публикует точные проверенные API/версии/ошибку и минимальный запрос к владельцу. Остальные продолжают автономное Python/skill/docs/package payload. Недоступный production Native install остаётся BLOCKED, не ложный PASS. Нельзя компенсировать это новым владельцем SQLite или собственным scheduler.

Пять Native suites сохраняют смысл exact/work/compact/cancel/retry/reopen/denial/admission/leases/4-8 faux. Loader paths определяются из явного test environment/установки пользователя; никакого встроенного host-lane. Зафиксированный SOURCE baseline не является результатом тестов TARGET.

## Skill/launcher и пакет

Раздельные server/observer, один invocation/run, exact sessions, initial-input markers и uncertain-outcome reconciliation сохраняются. Исходный approved prompt/plan/references фиксируются без экспорта личной беседы. Доступность Tern — явная UI capability; без него Python/extension остаются usable, никакой молчаливой установки. Скилл должен диагностировать неподдерживаемый transport/SDK, а не имитировать admission.

Alice владеет root manifest/files whitelist и локальным artifact build. Native package keys/entrypoint согласуются по Bob PUB-03; portable skill configuration — по Carol PUB-04. Без чистой проверки assembled artifact в disposable HOME нельзя заявлять install/update/uninstall PASS. Никаких public push/npm publish/release, установки в действующий HOME или глобальных регистраций этим поручением не разрешено.

## Происхождение, лицензии и public safety

Upstream MIT включается дословно: copyright (c) 2026-2027 Yuzhen Mao, Azalia Mirhoseini. Ссылка не заменяет полный license. Исходный DeLM checkout на указанном commit сейчас чистый, не патчится. Archived product plugin — отдельный MIT источник идеи/контрактов, не runtime, не переносить его Rust/macOS runtime.

`provenance.json` связывает source paths/commit/SHA256 с поставкой и статусом original/adapted/new; `parity.json` связывает пользовательскую функцию с модулем и проверкой. Начальный inventory — план включения/источник, не уже проверенный final artifact hash. Final hashes обновляются после реальных edits/tests. Старые отчёты/скриншоты/SQLite/.local/.git/private Config/auth/traces не копируются.

Лицензия наших частей, имя/владелец публичного repo и фактический push/release требуют отдельного решения владельца перед публикацией. До решения — локальная unpublished подготовка с явным legal/publication gate, не самовольное назначение MIT нашим частям. Этот gate не мешает безопасной реализации и локальным тестам.
