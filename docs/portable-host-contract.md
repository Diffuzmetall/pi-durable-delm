# HOST-01: Native board/config/package contract

Новая задача: [portable-host-assignment.md](portable-host-assignment.md). Прямое уточнение пользователя, записанное в context 639: нужен обычный Native Durable с минимальным прозрачным API-патчем; Pocket отвергнут. Прежние предложения Alice о Pocket superseded и не являются продуктовой архитектурой. Историческая Pocket fixture остаётся только доказательством исследованной альтернативы, не приёмкой этого продукта.

## Реальный Native host

**Продукт содержит только DeLM board, skill и extension.** Пользовательский Native уже установлен и сам владеет models/auth/settings, registry, scheduler, Harness и сессиями. Здесь нет поставки, установки или автоматического запуска другого Durable.

Независимые тесты используют публичный Native v1.0.2, commit `cd32f7725fdbddbaecdff5b1e68491563394e0ca`, с **явным минимальным трёхфайловым API-патчем** `extensions/delm/public-host-api.patch`. Source snapshot находится вне продукта, только в тестовой среде. Непатченный host без этой capability не поддерживается; SDK library regression 1.4.0 не означает совместимость любого Native 1.4. Рабочая установка автора не меняется.

Реальный Native DeLM E2E теперь проверен: два bound worker, board/result/event, EXACT ALL-DONE и available work, правильная root continuation, actual CLI snapshot/read/ACK, dedup/bindings/cancel, pending wait через server restart и настоящий plugin reload, existing beforeTool denial и настоящий PTY draft через DeLM wake. В этом сценарии 24 deterministic HTTP requests и 0 live LLM. Setup заранее закрепляет владельцев outputs, а model делает реальный claim replay; это не доказательство свежей конкурирующей autonomous claim. Отдельный реальный launcher проверил bootstrap/notify/lost response/stop/exact restart/resume/draft с 3 HTTP requests. См. [clean-native-host-verification.md](clean-native-host-verification.md) и `tests/launcher/HostSelfVerification.json`. Это компонентная приёмка, не финальная installed-archive HOST05.

Настоящие API gaps — отсутствие доступного registry/task seam и idempotent input ID в старом controller, а не обязательная private Hindsight-политика. Bob устранил ложную обязательность дополнительного admitInput в SDK adapter: публичный native submit использует реальные inherited guards, optional дополнительная существующая host policy не заменяется allow-all.

## Минимальный API и package entry

Патч предоставляет LOCAL-only `DurableSession.get(context)`: версия API 1, EXISTING registry/Harness/root и реальные metadata `sessionId/workspace/sessionPath`. Реальный server отказал remote RPC к этой LOCAL capability даже клиенту без собственного local flag; проверка входит в Native fixture. Новый владелец SQLite, копирование host или частного controller недопустимы.

Package declaration: `chord.facets.session = extensions/delm/session-facet.js`, корректный default export facets, `chord.external` включает `@earendil-works/pi-coding-agent/experimental/plugin`. Обычный существующий Native loader сам собирает package в свой `data/plugin-builds`; продукту не нужен собственный bundler/host installer. Package root сохраняет SDK registry adapter. `pi.extensions=[]` остаётся: нельзя подсунуть Durable adapter обычному Pi ExtensionAPI. SDK peers ограничены 1.0.2 и проверенным library baseline 1.4.0; public client transport peer — `@earendil-works/pi-client@1.0.2`. Это библиотеки, не dependency на Native host `pi-coding-agent`. Точный API/bundle release — `tests/native/host-evidence/native-final/candidate.json` и [native-compatibility.md](native-compatibility.md).

`delm.control` — удалённый продуктовый facet над тем же existing owner:

- `identity(ctx)` возвращает protocol/build и настоящие `sessionId/sessionPath/workspace/conversationId/instanceId`, binding/stopped.
- `bind({identity,run,actor},ctx)` фиксирует immutable actor/run binding при совпадении реального cwd/session.
- `input({identity,type,requestId,text,expectedSha256},ctx)` сохраняет durable approved SHA/type/request identity; иной payload под прежним ID отвергается.
- `status({identity},ctx)`, `resume({identity},ctx)` без dummy input и `stop({identity},ctx)` только своей bound session/собственных wakers.

Instance identity хранится в Native document: устаревший адрес или переиспользованный session ID не подтверждает новую сессию. Reload generation не даёт прежнему facet удалить replacement; restart восстанавливает binding из существующего Native storage. Эти binding/restart/reload свойства подтверждены настоящим Native компонентным сценарием. Installed payload и stop при pending/committed delivery остаются отдельной финальной проверкой HOST05.

Launcher использует только public `pi-client`, Unix transport и Chord bindings, не host-internal modules; `SessionManagement.create` с заранее сохранённым стабильным ID, exact attach/SessionDirectory и control facet. Нормальный `start` получает только explicit `--socket` уже работающего совместимого Native; `--host-source` — необязательный advanced test dependency resolver, не требование установки. Неопределённый ответ сверяется по прежнему ID; нельзя создавать новую случайную команду или использовать общий --continue. Server cwd должен совпадать с утверждённым workspace; mismatch диагностируется, а не исправляется сменой чужого server cwd.

## Существующий bundled board protocol

`project_events` выдаёт `protocol:2`; это наша pinned Python адаптация, не произвольный upstream DeLM. Actor-bound CLI вызывает HTTP `action:domain`; actor определяется служебной identity, поле actor в payload отвергается. Loopback endpoint и tokens находятся в приватном RUN, не в package/evidence/model input.

`projection` не потребляет receipt; snapshot → фактическое чтение → explicit ACK сохраняются. Стабильный request_id, expected_revision/generation и changed-payload refusal остаются. Exact ждёт ВСЕ перечисленные DONE, work лишь подсказывает доступную работу. Native notification не равен чтению/ACK.

Доска владеет context.sqlite и attached bodies DB, Native отдельно владеет своими сессиями. Расширение не пишет SQL live Native и не создаёт второго owner. Существующего protocol 2 достаточно; новый transport/health/config layer ради вида не добавляется.

## Конфигурация и безопасная поставка

Корень установленного package определяется его файлами; пользовательский RUN находится вне workspace. Никаких author paths/settings/credentials в runtime. Bindings берутся из trusted host context/config, не из model arguments или board publications. Shared init SDK adapter не является сам по себе доказательством Native plugin discovery: настоящая загрузка проходит через Chord session facet.

Пользователь добавляет DeLM package к своему обычному Native extension profile, **сохраняя остальные plugins/guards**. Client `prepareSession(packagePaths:null)` наследует существующий выбор; явный список заменяет его, поэтому launcher не подставляет один DeLM вместо пользовательского списка. Skill подключается штатным Native `loadSkills`: project-local `.pi/skills/delm` или уже разрешённый user skill path, без изменения глобальных настроек. Link создаётся только при отсутствии чужого entry; окончательный HOST05 должен подтвердить descriptor packaged skill в настоящем Native model prompt. `pi.skills` manifest сам по себе доказывает лишь обычный Pi package discovery.

`init --plan` один раз читает approved bytes до создания RUN, сохраняет `RUN/inputs/approved-plan.md` (0600, inputs0700), START указывает только frozen authority; original path остаётся provenance. Launcher не перезаписывает capture изменённым оригиналом. Финальные 48 core и все 10 packaging tests прошли на последних runtime bytes, включая 3 frozen-plan проверки, реальный offline npm cache filter и plain installed CLI без bytecode/cache pollution. Startup hint теперь работает из любого cwd и указывает пользовательский interpreter/installed script.

Существующий versioned payload installer сохраняет user edits и RUN/history; Node/Native plugin lifetime и отмена принадлежат реальному Native control, не файловому установщику. Python CLI больше не создаёт bytecode в immutable trees. Фильтрация caches исправлена nested build-only .npmignore, реальный offline npm pack regression PASS; это не host acceptance.

Новые собственные Pocket installer/test Alice убраны из продуктового дерева с сохранённой приватной backup-копией; Pocket subpath/peer1.1 удалены. Общие frozen-plan/cache/packlist исправления и работа остальных сохранены. No commit/push/publication или live-model smoke не разрешены новой задачей.

## Проверка и владение

Bob: API patch/facet/native tests. Carol: обязательный skill workflow, exact-session launcher/input/control. Dave: настоящая изолированная Native fixture и итоговая приёмка; Alice/Carol независимо проверяют fixture на крупной вехе. Alice: Python/config/package/provenance. Общие paths сериализуются, один unfinished claim на actor.

Текущий assembled archive проверяет 34 source/license assets; vendor содержит только DeLM, Native MIT notice — только `LICENSES/pi-native.txt`, не host code. Installed CLI и официальный public Chord bundle/integrity loader отдельно проходят; это не подмена real Native E2E.

HOST05 проверяет установленный полный archive, нормальное обнаружение skill и extension, свежую claim/result/event/readACK цепочку, pending/committed stop, update/disable/remove с сохранением project/RUN/conversations и финальный quickstart. Carol независимо приняла Native fixture source/evidence (73 fingerprints); Alice/Carol рассматривают финальную QA fixture без новых агентов. SDK/faux, real deterministic Native и отдельно разрешаемый live smoke отмечаются раздельно. Historical evidence не становится свежим PASS; no live-model/commit/push/publication authorization.
