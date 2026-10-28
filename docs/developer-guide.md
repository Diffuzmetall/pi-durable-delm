# Руководство разработчика DeLM

Назначение: понять код, границы ответственности, рабочий цикл и проверки до изменения реализации. Текущий [статус поставки](project-status.md), [план/задачи](delivery-plan.md) и [карта документов](index.md) дополняют это руководство.

## 1. Компоненты и владельцы

| Путь | Ответственность | Не его полномочия |
|---|---|---|
| `vendor/DeLM/` | Закреплённые upstream Python primitives и MIT notices | Не ядро Native; не Rust runtime другого плагина |
| `scripts/delm_local.py`, `bin/delm` | HTTP/CLI/auth boundary, создание RUN, actor binding и bootstrap | Не запуск произвольного host и не выдача разрешения на модель |
| `scripts/delm_domain.py` | Канонические task/publication/lifecycle projection и мутации | Не отдельный scheduler |
| `scripts/delm_delivery.py` | Persisted snapshots, replay, pending, ACK в той же board DB | Не подтверждение понимания моделью |
| `scripts/delm_leases.py` | Нормализация paths/resources, ownership/TTL/conflicts | Не блокировка всех shell writers |
| `scripts/delm_board.py` | Curses read-only observer, детали, история и поиск | Не источник задач и не потребитель actor cursor |
| `extensions/delm/index.js`, `protocol.js` | Native wait/watch/relevance/delivery/recovery | Не второй владелец Native storage |
| `extensions/delm/native14.js`, `native14-owner.js` | Adapter к текущему owner/controller; private control | Не замена настоящего admission |
| `skills/delm/Tools/Run.py` | Prepare/open/start/notify/status/stop/resume и actor ledger | Не terminal manager, auth manager или model supervisor |
| `NativeControl.mjs`, `NativeInput.mjs` в `skills/delm/Tools/` | Транспорт и approved input/replay binding | Не изменение текста под прежним request ID |
| `packaging/install.py` | Управляемые версии payload, update/rollback/remove | Не установка Native и не удаление RUN |
| `tests/`, `evidence/native14/`, `docs/evidence/` | Проверки и история доказательств разных этапов | Не универсальное доказательство совместимости любого host |

## 2. Где хранятся данные

Workspace содержит общие исходники и результат. Приватный RUN содержит board metadata, инструкции, endpoints, actor-bound CLI, launch identities, inputs и секреты доступа. Его нельзя публиковать.

Доска использует `context.sqlite` и `context-bodies.sqlite`; второе хранилище содержит тела/вложения, а не независимую очередь. Native хранит собственные sessions, разговоры, принятые inputs и scheduler. Доступ к нему — через существующий SDK/controller, не прямые SQL-записи.

Нет общей транзакции между board SQLite, Native storage и внешним shell-эффектом. Stable replay и reconciliation закрывают конкретные неопределённые исходы; они не превращают любое внешнее действие в exactly-once.

## 3. Основной рабочий цикл

1. Пользователь задаёт результат, scope и разрешённые модели/участников. Скилл читает применимые правила и план.
2. `prepare` фиксирует inputs и RUN, не вызывая модель. `serve` владеет board backend.
3. Для каждого actor `open` запускает уже установленный Native в обычном терминале с его bound adapter. Identity фактического owner фиксируется до ввода.
4. `start` отправляет утверждённые bytes с типом, SHA и стабильным request ID. Реальный controller выполняет admission; затем SDK submit использует тот же ID.
5. Агент читает свежую доску, выбирает полезную READY-задачу и выигрывает claim. Revision и generation защищают от устаревшей команды; один actor не держит две unfinished claims.
6. Пригодный ранний выход завершается отдельно. Потребитель берёт общий файл без apply/copy и не ждёт необязательный остаток producer.
7. Если независимой работы нет, агент вызывает Native `delm_wait` на точные task IDs и завершает ход. Ожидание хранится в существующем Native scheduler.
8. После события компактная ссылка продолжает ту же root conversation. Агент получает сохранённый snapshot, действительно читает его и явно ACK-ает receipt.
9. Автор проверяет свою задачу. На крупной вехе другой существующий peer проверяет source/QA; итоговая приёмка не подменяется одним DONE или видимым окном.

## 4. Состояния, которые нельзя смешивать

| Одно состояние | Не означает другое |
|---|---|
| FACT опубликован | Точная зависимость DONE |
| Reviewer закончил работу | Его verdict обязательно PASS |
| Важная correction/смена owner | Успешная readiness |
| Watcher обнаружил событие | Модель прочитала его |
| Native принял компактный input | Actor подтвердил полный receipt |
| Lease истёк | Процесс writer умер |
| Actor idle или закончил ход | Producer окончательно ended |
| Исходный файл обновлён | Работающий процесс загрузил новые bytes |
| SDK import прошёл | Реальный установленный host совместим |
| Commit создан | Remote branch обновлена |

Parent/output dependencies проверяются как completion prerequisites; metadata parent back-pointer не превращается в зависимость. Нельзя обходить цикл или незавершённые outputs отметкой parent DONE. Точные поля и ошибки: [domain protocol](DeLM-domain-protocol.md).

## 5. Trust boundary Native 1.4

Текущий entry сохраняет исходные registry extensions, hooks и owner lifecycle. Требуется реально существующий выбранный admission controller. Отсутствие capability — unsupported host, не повод заменить policy на allow-all. Current control socket живёт внутри того же процесса; он не вводит новый runtime.

Проверяются canonical run/actor/workspace, физический session path, root и persistent instance. Совпадение conversation1 само по себе недостаточно. Correlation `id` транспорта не равен durable `requestId`. Повтор после потери ответа сохраняет исходные type/text/SHA/ID; изменённый replay отвергается.

Перед и после реального admission проверяется active/stopped boundary. `stop` и отмена waiter не обещают отозвать уже принятое сообщение или уничтожить произвольный внешний процесс. `resume` не отправляет editor draft или dummy input. Точный [ABI](native14-contract.md) важнее этого обзора.

## 6. Проверки по слоям

| Уровень | Что доказывает | Что не доказывает |
|---|---|---|
| Python domain/HTTP/CLI | Транзакции, граф, fences, snapshots, leases, conformance | Native loader и модельное решение |
| Native SDK/faux | Настоящие scheduler/storage и заданные callback-сценарии | Любой внешний host и качество LLM |
| Actual-host fixture | Реальные launcher/main/registry/controller/tools с MODEL-only заменой | Новые bytes в живой команде |
| Installed artifact | Состав/hashes, поведение ровно установленных файлов | Любой следующий архив с другими bytes |
| Curses PTY | Интерактивные клавиши, paints, resize, quit | Принятие модели и чтение за агента |
| Git remote verification | Доставка source commit на точную ветку | npm release, deployment и runtime activation |

Полный Native fixture допускает только явно разрешённые deterministic/faux вызовы; не запускайте его автоматически из-за изменения текста. Простой документационный контроль:

```bash
python3 -B skills/delm/Tools/Run.py --help
python3 -B scripts/delm_board.py --help
python3 -B -m unittest discover -s tests/native14-package -p test_package.py -v
```

Последняя команда собирает offline payload во временной области, проверяет install/remove и карту настройки; не зовёт Native-модель. Наличие npm и локальной test environment проверяют до запуска. Native/model reproduction из [приёмки](native14-acceptance.md) запускают только с нужными разрешениями и с учётом её [поправки](../evidence/native14/acceptance/postremove-supplement.md).

## 7. Работа с историей и изменениями

Править надо причину у её владельца: graph invariant — в domain boundary; receipt loss — в delivery; approval/replay — в Native input; viewer consumption — в observer. Не заводить второй tracker/Harness или условную текстовую эвристику вместо явных links.

Принятые evidence не исправляют задним числом. Новый bounded probe или correction имеет отдельный manifest, scope и явное указание, какой вывод заменён. Нельзя складывать 17 прежних и 19 новых faux-запросов в рассказ об одном зелёном запуске.

Обзорные документы обновляют ссылкой на [общий статус](project-status.md). Новые operational claims проверяют по текущему owning source и help. Учебные правила хранятся в [compound store](solutions/workflow-issues/completion-evidence-chain.md); разрешения и guards из них не расширяются.
