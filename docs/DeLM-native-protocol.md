# Ожидания и доставка Native

Этот документ описывает сохраняемый контракт компонента. Сам по себе он не доказывает совместимость с production Native: host должен предоставить доверенную admission capability. Нельзя заменить её прямым `submit`, заглушкой «разрешить всё» или тестовым FauxHost. Результат проверки API и версий публикуется отдельно в `docs/native-compatibility.md`.

## Два ожидания

**Нужен определённый результат:**

```text
delm_wait(action="wait", items=["точные UUID задач"], reason="нужен контракт")
```

READY требует DONE **всех** названных задач и отсутствия связанных нерешённых FAIL. Завершение раннего output не завершает родителя или оставшуюся работу автора. Посторонний FACT не меняет predicate.

Связанный FAIL, correction/resolution после регистрации, blocked dependency, явно ended producer или смена ownership epoch могут вызвать **reevaluation**, а не READY. Уже известная проблема возвращает `reevaluateNow:true, readyNow:false`; её надо разобрать, а не бесконечно переустанавливать ожидание. Idle и обычный конец хода не означают смерть производителя.

**Свободен и готов взять следующую работу:**

```text
delm_wait(action="work", reason="следующий разрешённый полезный результат")
```

`items` не передают. Actor должен быть свободен: без незавершённого claimed/blocked task и blocked/ended lifecycle. Доступная работа возвращает `workAvailableNow:true`, не READY конкретной зависимости. Иначе один persisted watcher ждёт готовую работу или прямой handoff этому actor.

Пробуждение не назначает и не резервирует задачу. Участник читает доску и выигрывает атомарный claim; конкурент может успеть раньше. Нет гарантии справедливого распределения или одного wake на задачу. После admission и получения snapshot доступность проверяется заново; исчезнувший hint не отправляется модели. FACT и ещё неготовая задача не вызывают ненужный model input.

Если весь разрешённый план закончен, нужно завершить поручение, а не ждать необязательного продолжения. Старое exact wait не преобразуется в work автоматически. Перед новым ожиданием проверяют прежнее через status и при необходимости штатно отменяют.

## Уведомление — ссылка, не чтение

Продолжение содержит не более **2048 UTF-8 байт**: READY / WORK AVAILABLE / REEVALUATE-NOT-READY, короткую причину, ограниченный набор IDs, receipt/request ID, диапазон sequence и команды bound CLI. Полная очередь и журнал остаются в сохранённом snapshot Python-доски.

1. Выполнить указанную команду `context domain` с **исходным** snapshot request ID.
2. Прочитать весь ответ, включая связанные ошибки и ограничения.
3. Явно ACK именно этот receipt.
4. Перед claim сверить свежее состояние: immutable snapshot не исключает последующих изменений.

Принятие короткого reference не двигает cursor. До явного read/ACK receipt остаётся в pending; status показывает `awaiting-read`, а после подтверждения — `acked`. Observer и watcher не читают за модель. Потерянный ответ snapshot восстанавливается повторением того же request ID.

## Сохранение и recovery

Python владеет board events и receipt body. Native владеет существующим conversation, scheduler, документом ожиданий и submission receipts; нового runtime или второго владельца Native SQLite нет. Actor/root/workspace берутся из доверенной привязки, не из аргументов модели.

Нативный input сохраняет стабильный `delm-wake:<originalTaskId>` при retry и повторном открытии. До submit фиксируются reference metadata, actual trigger, delivery mode и dispatch intent. После trusted admission trigger перепроверяется. Work snapshots дополнительно различаются board sequence, чтобы позднее новое предложение не проигрывало устаревший hint.

Если ответ submit потерялся после принятия, recovery находит прежний input и не отправляет второй. Принятый reference всё равно не autoACK. Между Python и Native нет общей транзакции; это reconciliation двух сохранённых состояний, не обещание атомарного cross-DB commit.

Исторический accepted **inline** input уже содержал полное тело receipt и сохраняет прежний autoACK recovery. Новый reference нельзя спутать с ним: mode фиксируется до submit. Старый ещё не принятый inline entry переводится в reference перед первой новой отправкой. История не удаляется.

## Status, retry и cancel

```text
delm_wait(action="status")
delm_wait(action="retry", id="точный ID failed wait")
delm_wait(action="cancel", id="точный ID wait")
```

Status различает `waiting`, `sent`, `failed`, `cancelled`, trigger и delivery state; свежий ACK сверяется с bound pending. Недоступный backend не позволяет объявить ACK успешным. После восстановления конкретной проблемы retry использует исходный submission ID и receipt, не создавая новую domain task.

Cancel допустим до committed dispatch, включая failed unaccepted delivery. После dispatch commit отмена отказывает (`cancelRefused`, `dispatchCommitted`, при известном принятии — `accepted`): нельзя обещать отозвать уже отправляемый или принятый input. Failed submit без accepted receipt освобождает dispatch intent. Cancel не подтверждает непрочитанный snapshot, не освобождает claim и не объявляет producer-ended.

## Проверка и откат

SDK/faux проверяет scheduler, SQLite, exact/work predicates, denial, response loss, cancel/reopen, compact notifications и 4/8 fixture identities без платных моделей. Это не доказательство eight-live-LLM capacity, stock-host admission или фактического live reload.

Перед downgrade до версии без `work` надо в текущей версии закончить/отменить все waiting/failed work-watchers и восстановить accepted deliveries. Старая версия может принять пустой items за «все зависимости DONE». Нельзя стирать wait history или менять Native SQL, чтобы обойти эту границу. Полный порядок — [operations.md](operations.md).
