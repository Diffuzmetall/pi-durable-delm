# HOST: переносимое подключение пользовательского Pi Durable

Новая явно разрешённая пользователем задача; существующая команда Alice/Bob/Carol/Dave, прежняя доска context. Это реализация следующего этапа, не повторная публикация и не повтор старого отчёта о блокировке. Репозиторий: https://github.com/Diffuzmetall/pi-durable-delm . Все продуктовые изменения — в его checkout. Рабочую установку автора и прежний source/run не менять.

## Требуемый результат

Пользователь скачивает пакет, подключает расширение к СВОЕМУ поддерживаемому Pi Durable и работает с агентами через общую DeLM-доску. Его модели, credentials, настройки, workspace и сессии остаются его. Установка/приватный host/Hindsight controller/абсолютные пути автора не нужны. Нужен доказанный сценарий на настоящем независимом host, а не только SDK-компонент или faux PASS.

## Прочитать до выбора реализации

- Свой действующий START и контракт координации. Их старые completed-slice и старый gate — история, не доказательство новой несовместимости. Активные START/WORKER не редактировать.
- release-readiness.md, README.md, docs/native-compatibility.md, docs/architecture.md, docs/operations.md, docs/publication-checks.md.
- extensions/delm/, skills/delm/Tools/, package.json, свои вызывающие стороны и существующие тесты.
- Документы и реальные exports фактически выбранного ПУБЛИЧНОГО host/CLI/SDK. Ordinary Pi ExtensionAPI, Durable SDK и конкретный host — разные интерфейсы.

Проверить актуальность прежних утверждений: Python работает отдельно; SDK adapter требует admitInput; start/resume/notify/stop раньше отказывали; частная установка добавляла свой контроллер. Старое решение не обязательная архитектура. Определить, нужна ли дополнительная admission-политика обычному host, либо только частной установке автора. Не держать частную зависимость вечным blocker и не заменять её allow-all; сохранить настоящие host guards и workspace permissions.

## Реализация

1. Поддерживаемое обнаружение/загрузка расширения НАСТОЯЩИМ пользовательским Durable, конфигурация доски, bindings workspace/run/actor/exact session. Существующий владелец сессии, штатные scheduler/storage; никакого второго Harness/владельца live DB или копии приватного host под видом plugin.
2. Чтение, claim, публикация результата, snapshot/read/ACK; exact ALL-DONE и отдельный available-work wait. Board event возобновляет правильную беседу без model polling. Stable request identity, отказ неверным bindings, повтору с другим approved input/type, корректные cancel/restart/reload/reopen.
3. Реальные prepare/start/resume/notify/stop через поддержанный host, только созданные/привязанные точные сессии. Сохранить несданный editor draft, исходный утверждённый prompt/plan/references и не создавать второй запуск/ввод после неопределённого ответа. Существующее durable request-to-input fingerprint исправление сохраняется.
4. Проверенные команды скачать → подключить → запустить → увидеть результат → остановить. Версии/prerequisites, понятный отказ неподдерживаемой версии/отсутствующего capability, безопасное отключение/удаление без удаления projects/RUN/conversations.

Bundled Python остаётся поддержанной адаптацией. Board protocol и его версия отделены от физического checkout; произвольный upstream board не обещать совместимым. Поддержка непосредственного upstream server потребует отдельной проверки протокола/версии.

Если публичному Durable действительно не хватает API: установить точный недостающий контракт/версию, показать проверенный путь исполнения и минимальное решение в самом upstream/plugin API. Это реальная причина BLOCKED, но не DONE за наличие ещё одного отчёта. Проверить разумную альтернативу прямому частному adapter, прежде чем объявлять отсутствие поддержки.

## Приёмка на изолированной пользовательской среде

Настоящий публичный поддержанный Durable host, пустой HOME/config/project, без личной среды автора. Допустим deterministic model provider ВНУТРИ настоящего host; mocks host/discovery/admission или самостоятельный demo Harness не закрывают E2E.

- Установка документированным способом и подтверждённая загрузка plugin реальным host.
- Доска, два участника и один workspace.
- claim → результат → board event → правильная session resume → snapshot/read/ACK.
- Повтор события/request не даёт повторной работы; changed approved payload под тем же ID отвергается.
- Wrong actor/workspace/session отвергаются.
- Exact ждёт ВСЕ зависимости; work отдельно ждёт доступную работу; FACT не означает DONE.
- Cancel, reload/restart и продолжение прежних точных сессий.
- Реальное сохранение editor draft, без его отправки.
- Отключение/удаление сохраняет projects/RUN/conversations.
- Релевантные прежние тесты и новые regression/integration тесты.

Результаты SDK/faux, deterministic real-host и live-model разделить. Live-model smoke запрещён без отдельного явного разрешения на модели/расходы; его отсутствие не мешает закончить независимую реализацию и deterministic host acceptance.

## Границы и сохранность

Не менять рабочую установку автора, global settings/credentials/существующие sessions. Не читать/публиковать личные беседы. Не писать SQL в live Durable DB, не создавать второго владельца. Не обходить tool/input/permissions/workspace guards. Никаких дополнительных LLM-агентов или платных сервисов. Пользователь разрешил изолированные dev/test зависимости, не глобальные; фактические frozen/tool ограничения не обходить, несовместимость разрешений показать предметно до запрещённого действия. Сначала использовать уже установленные публичные зависимости.

MIT/upstream notices, Python-функции и смысл протоколов сохраняются. Skills редактировать только через обязательный createskill workflow. Новая задача НЕ разрешает commit/push/PR/publish/deploy; прежнее разрешение публикации не переносить молча на новые изменения. Историческое evidence сохранять, новые проверки писать в новые пути, актуальные provenance hashes обновлять по конечным runtime bytes.

## Владение и координация

Только bound context и delm_wait; Tern используется для явно запрошенного kickoff тех же трёх бесед, не как второй tracker. Один unfinished claim на actor, claim до записи; общие пути — только явный handoff. Контракты/выходы публиковать рано с actual task IDs, не делать каждому полный независимый продукт. Никаких Mail/Beads/Goal/Loop/других model agents. Exact DONE является условием ожидания, не FACT и не claim.

- HOST-01 Alice: board/config/package contract; scripts/**, packaging/**, package.json, tests/packaging/**, provenance/parity, этот документ и docs/portable-host-contract.md.
- HOST-02 Bob: реальное public-host подключение; extensions/delm/**, tests/delm-*.test.mjs, tests/native/**, docs/native-compatibility.md. Рано публикует проверенный host entry/control contract для Carol/Alice.
- HOST-03 Carol: launcher/input/skill; skills/delm/**, tests/launcher/**. Ранняя подготовка независимо; реализация host control после реального контракта Bob/Dave.
- HOST-04 Dave: изолированный настоящий host и provider; tests/host/**, docs/clean-host-verification.md. Рано публикует actual host/discovery/version facts. Не переписывает продуктовый bridge Bob.
- HOST-05: крупная независимая приёмка и quickstart после первых четырёх. Dave проверяет чужие продуктовые границы, Alice/Carol независимо проверяют fixture/acceptance harness Dave; никто не объявляет собственный host mock за независимое доказательство. Общие manifest/metadata — сериализованный handoff Alice.

Остановиться только после выполненного проверенного сценария или настоящего внешнего/API/permission blocker после разумной самостоятельной проверки альтернатив и завершения всех независимых работ. Не останавливаться на сохранённом prompt, файлах расширения, установленном SDK или старом faux PASS.
