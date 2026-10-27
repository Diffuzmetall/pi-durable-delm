# Доска, actor-bound CLI и протокол v2

Это контракт Python-слоя пакета, не отчёт о работающей production-интеграции Native. Реализация: `scripts/delm_local.py`, `delm_domain.py`, `delm_delivery.py`, `delm_leases.py`; исходная основа — `vendor/DeLM/board/protected_board.py`.

## Владение и транспорт

Python владеет событиями и задачами в существующей `context.sqlite`. Вложения используют attached `context-bodies.sqlite`. Native отдельно владеет исполнением. Никакого второго task tracker или владельца Native SQLite нет.

Старые операции CLI остаются совместимыми. Новые идут через `context domain '<JSON object>'`: bound executable выбирает actor и локальный HTTP endpoint из приватной привязки. Модель не передаёт actor или credentials. Не публикуйте `config.json` и не подставляйте чужой token.

HTTP-запрос использует прежний аутентифицированный POST transport с `action:"domain"`. Мутация выполняется в одной `BEGIN IMMEDIATE` транзакции. Ей нужен уникальный стабильный `request_id`: точное повторение возвращает сохранённый ответ, повторение с другим содержимым отвергается. Ошибки содержат `error` и `code`: `INVALID`, `UNKNOWN`, `CONFLICT`, `STALE`, `BLOCKED`.

## Чтение: snapshot → read → ACK

```bash
context domain '{"op":"snapshot","request_id":"read-001"}'
```

Ответ содержит `receipt_id`, `request_id`, `actor`, `from_sequence`, `to_sequence`, `full`, `view`. Сначала прочитайте весь `view`. Затем подставьте полученный receipt ID:

```bash
context domain '{"op":"ack","request_id":"read-001:ack","receipt_id":"<receipt_id>"}'
context domain '{"op":"pending"}'
```

Это пример API с явно обозначенным полем ответа, не готовая команда для чужого receipt. Потерян ответ — повторите исходный snapshot request, а не создавайте новый. Replay возвращает тот же снимок даже после новых событий. ACK двигает cursor только до сохранённого `to_sequence`, монотонно и идемпотентно; чужой actor не может подтвердить receipt.

Первое чтение полное, последующие сохраняют актуальную очередь и липкие blockers, но возвращают delta событий/публикаций после ACK. `full:true` нужен для явного восстановления. `pending` переживает потерю ответа и повторное открытие. Legacy `context read` не предоставляет этой гарантии доставки.

Для observer используется `context domain '{"op":"projection"}'`: он не создаёт receipt и не потребляет непрочитанное. Сам факт чтения watcher или доставки короткого уведомления не означает чтение полного тела.

## Задачи

Основные поля: `id`, `subject`, `detail`, `state`, `owner`, `generation`, `revision`, `deps`, `criteria`, `parent`, `outputs`, `mapping`. Состояния: `open`, `claimed`, `blocked`, `done`. UUID — mutation identity; display key observer не заменяет UUID в API.

| `op` | Дополнительные аргументы |
|---|---|
| `create` | `subject`, `detail`, `deps:[]`, `criteria:[]`, необязательный `parent` |
| `claim` | `item`, `expected_revision` |
| `update` | `item`, `expected_revision`, `generation`, `changes` |
| `split` | те же fences, `children:[{subject,detail,deps,criteria,mapping}]` |
| `release` | те же fences, `summary` |
| `handoff` | те же fences, `summary`, `to` |
| `complete` | те же fences, `summary` |

Все мутации также требуют `request_id`. Служебные значения берут из свежего ответа доски, не угадывают. Для update/split/release/handoff/complete нужны текущий owner и claimed state. Claim допускается только для готовой open-задачи и свободного actor. Handoff передаёт задачу свободному разрешённому получателю одной транзакцией.

`revision` — sequence последнего task event; `generation` меняется при передаче, освобождении и reclaim. Старый writer не может закрыть переданную задачу. При `STALE` сначала сверяют checkpoint и владельца; слепая подстановка нового счётчика не восстанавливает разрешение на запись.

Готовность вычисляется из всех deps и связанных blockers, а не из текста FACT. Completion prerequisites включают **deps + outputs**: прямые и транзитивные циклы отвергаются атомарно. `parent` — метаданные, не обратная зависимость. Split сохраняет критерии родителя через mapping, не завершает его автоматически; complete требует DONE всех deps/outputs и отсутствия связанного FAIL.

## Публикации и ошибки

`publish` принимает `type` (`FACT`, `FAIL`, `CORRECTION`, `RESOLUTION`), `text`, необязательные `task`, `related:[]`, `output`, `readiness`, `limitations`, `resolves:[]`. Все ссылки должны существовать. `readiness:true` требует явно завершённого output.

FAIL остаётся blocker у связанных задач и зависящих потребителей до явного CORRECTION/RESOLUTION с его ID в `resolves`. Закрыть его может автор или связанный task owner. Фраза «починил» без ссылки не убирает blocker; история сохраняется. Несвязанный FAIL не служит глобальной кнопкой STOP.

## Lifecycle и восстановление

`lifecycle` принимает `state` (`active`, `idle`, `blocked`, `ended`), `reason`, `expected_generation` actor. Декларация меняет actor epoch; blocked/ended блокируют удерживаемые задачи и защищают их новым task generation. Idle, конец хода, закрытое окно и истёкшая бронь не равны ended.

`reclaim` требует точные task revision/generation, `producer_generation`, checkpoint `summary` и `acknowledge_external_writes:true`; разрешён лишь после явного ended прежнего владельца. Старые leases не исчезают автоматически. `resume` позволяет исходному владельцу продолжить blocked checkpoint после явного active lifecycle, с точными fences и summary.

Пропавший без ended производитель требует конкретного внешнего подтверждения и разбора оставленных writers. Нельзя объявить его умершим по TTL или забрать работу поверх работающего shell.

## Бронь путей и ресурсов

Операции `lease-acquire`, `lease-renew`, `lease-release`, `lease-handoff` требуют task/generation и request ID. Acquire добавляет `paths:[]`, `resources:[]`, `ttl`; renew/release используют `lease_id`; handoff также `to` после согласованной передачи задачи.

Пути нормализуются внутри workspace, включая symlinks и ещё не созданные дочерние файлы. Бронь корня, выход наружу и пересечения «каталог — потомок» запрещены. Несколько путей выдаются атомарно. Ключи ресурсов конфликтуют по точному равенству. TTL по умолчанию 300 секунд, диапазон 1–86400; продление явное.

Бронь advisory: не перехватывает write/edit и произвольный shell. Истечение убирает разрешение, но не останавливает процесс. Перед handoff нужен checkpoint и остановка прежнего writer; task-handoff и lease-handoff — разные действия. Освобождайте бронь до complete.

## Проекция и совместимость

`project_events(rows, actors=())` — чистая функция: возвращает `protocol:2`, sequence, agents, queue (включая DONE), notes, blockers, sessions и всю историю events. Legacy item/claim/done/note/session не переписываются; неизвестные события остаются в истории. Receipt/lease tables создаются аддитивно в той же базе, с caller-owned транзакцией. Модули delivery/leases не открывают и не коммитят собственную БД.

Legacy isolated-режим с `--source` остаётся отдельным сценарием: у участников свои workspaces. Shared-режим использует `--shared-workspace` и запрещает apply. Не переносите правила isolated-копирования в общую папку. Подробности эксплуатации — [operations.md](operations.md), ожиданий — [Native protocol](DeLM-native-protocol.md).
