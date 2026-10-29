# Руководство пользователя DeLM

DeLM даёт нескольким агентам общие задачи и результаты в одном проекте. Для маленькой последовательной правки команда не обязательна. При независимых направлениях она позволяет передать пригодный выход раньше окончания всей работы автора.

Это руководство объясняет полный маршрут и ожидаемые состояния. Точные команды получения/установки даны в [README](../README.md), аргументы текущего launcher — в [справке](../skills/delm/Tools/Run.help.md). [Итоговый статус и ограничения](project-status.md).

## До запуска

Нужны POSIX-среда, Python 3.10+ с `sqlite3`, для интерактивного TUI — `curses`; уже установленный совместимый Native Pi Durable 1.4 и его matching SDK 1.4.0. Текущий Node requirement — не ниже 22.19.0. Номер SDK не заменяет проверку реального [host-контракта](native14-contract.md).

Определите workspace, план, исходный утверждённый prompt, применимые правила и число участников. Roster 2/4/8 — возможность конфигурации; разрешение запустить соответствующие модели и расходы нужно отдельно. Не используйте настоящие рабочие беседы для dummy smoke.

Самый короткий путь: передайте агенту [готовый запрос настройки](../prompts/setup-delm.md) и ссылку на репозиторий. Он не должен устанавливать другой Durable, переписывать auth/settings или отключать guards. Если capability отсутствует, правильный результат — конкретный blocker, не обещание работающей интеграции.

## 1. Получить payload

Следуйте [установке из README](../README.md#получить-и-установить-пакет): checkout → `npm pack --ignore-scripts` → проверка состава → `packaging/install.py install` в свой prefix. Это не npm publish и не установка Native.

Ожидаемые состояния: `installed` при первой установке, `unchanged` при повторе ровно того же архива. `native_registered:false` нормально: это ещё только файлы payload, не загруженное расширение и не запущенные модели. `PACKAGE` указывает на управляемую текущую версию.

## 2. Сначала проверить доску без моделей

[Демо README](../README.md#попробовать-доску-без-моделей) создаёт новый синтетический RUN. Backend запускается как отдельный foreground `serve`; в другом терминале открывается:

```bash
python3 "$PACKAGE/scripts/delm_board.py" "$RUN" --observe
```

Ожидается `DeLM BOARD | READ ONLY`. Держите доску постоянно видимой рядом с агентами; для четырёх участников — доска слева, агенты справа 2×2. [Раскладка, тема до старта и безопасное переоткрытие](terminal-layout.md). `q` закрывает viewer, а не backend. Режим `--once` печатает один снимок, но не доказывает интерактивность. Не делайте новый `init` для восстановления уже существующего RUN.

## 3. Подключить скилл и подготовить команду

До создания workers подключите `$PACKAGE/skills/delm` project-local ссылкой по [атомарной инструкции README](../README.md#подключить-скилл). Существующая запись назначения не перезаписывается. Отказ — повод проверить владельца/target, а не удалить каталог.

Задайте разрешённые пути `PROJECT`, `PLAN`, `APPROVED_PROMPT`, `GLOBAL_AGENTS`; `RUN` должен быть новым приватным каталогом вне workspace. `GLOBAL_AGENTS` — разрешённый файл правил, не credentials/config.

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" prepare \
  --workspace "$PROJECT" --plan "$PLAN" --prompt-file "$APPROVED_PROMPT" \
  --global-agents "$GLOBAL_AGENTS" --agents 2 --run-dir "$RUN"
```

Ожидается сохранение inputs и команды backend/observer/actor open. Модель ещё не запущена. Подготовленные START/WORKER не доказывают принятие первого input.

## 4. Открыть Native и начать работу

1. Выполните напечатанную команду `serve` в терминале backend.
2. В двух отдельных обычных интерактивных терминалах:

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor alice
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor bob
```

3. Дождитесь готовности endpoints. При уже разрешённом model launch:

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" start --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" status --run-dir "$RUN"
```

`open` исполняет существующий Native с точным adapter. `start` доставляет approved input уже открытым участникам, не создаёт окна. Терминальный менеджер не требуется. До acceptance input видимый процесс — ещё не работающий агент по вашему заданию.

## 5. Как агенты взаимодействуют

Агент читает доску и выигрывает claim, прежде чем менять общий файл. Закончив полезный output, он публикует evidence и DONE этой задачи. Другой агент использует тот же файл без копирования. Один DONE не принимает весь проект.

При отсутствии независимой работы агент вызывает `delm_wait` с точными IDs и заканчивает ход. Готовность требует всех DONE. Связанный FAIL, смена owner или correction могут потребовать переоценки, но не означают успешный результат. После wake агент читает сохранённый snapshot и явно подтверждает ACK; TUI не делает это за него.

В observer: стрелки/`j`/`k` — строка, Enter — детали, Tab — задачи/заметки, `/` — поиск, `l` — журнал, `q` — выход. При узком терминале увеличьте окно. Leases и claim помогают согласовать работу, но не блокируют произвольный чужой shell.

## 6. Уведомить, остановить, продолжить

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" notify --run-dir "$RUN" \
  --actor alice --input-file "$APPROVED_UPDATE" --request-id approved-update-001
python3 "$PACKAGE/skills/delm/Tools/Run.py" stop --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" resume --run-dir "$RUN"
```

После неопределённого ответа повторяют тот же request ID и те же bytes, не новый ID. `stop` не удаляет историю и не закрывает терминалы; `resume` не отправляет новый prompt. Несданный editor draft не является утверждённым вводом.

После нормального выхода Native повторяют **тот же actor open**, который использует записанную точную session. Пока процесс жив, возвращаются к его терминалу. Не используйте общий `--continue`, не открывайте второго владельца и не удаляйте lock. Закрытый терминал не гарантирует фоновую работу.

## 7. Backup, update и удаление

Остановите собственных writers и сверьте active waits/accepted inputs. Backup доски включает обе SQLite-базы с учётом WAL; Native сохраняют штатными средствами owner. Сохраните launch identities и drafts. Не копируйте личные базы в bug report.

Installer обновляет только управляемый payload. Rollback файлов не делает безопасным downgrade Native watchers сам по себе. Перед удалением отключите только DeLM при согласованном idle lifecycle и уберите только собственную проверенную skill-ссылку. Затем используйте сохранённый bootstrap `uninstall --prefix "$PREFIX"`. Изменённые деревья могут остаться в `retained`; это защита данных. RUN, workspace и Native sessions сохраняются.

## Диагностика

| Симптом | Безопасное действие |
|---|---|
| Нет trusted admission | Сверить host-контракт; не заменять policy |
| Endpoint не готов | Проверить RUN/actor и первую ошибку в терминале `open` |
| Session уже занята | Вернуться к действующему владельцу, не снимать lock |
| `STALE` или scope mismatch | Перечитать доску/identity, сверить revision/generation |
| Нет wake | Проверить точные DONE, relevant FAIL и pending/read/ACK |
| Пакет обновлён, поведение старое | Сверить реально загруженный build; файл на диске не hot reload |
| Светлые tool-блоки на тёмном экране | Проверить, была ли выбранная тема доступна до старта; [безопасно переоткрыть точные сессии](terminal-layout.md) только с разрешения пользователя |
| Модель ответила после removal | Это не отрицательный prompt-test; нужен настоящий current SDK witness |

Для отчёта приложите commit/hash, OS, точную команду, exit code и минимальный синтетический пример. Не прикладывайте RUN, tokens, auth/provider configs, Native SQLite, личные conversation dumps или неочищенные traces.

## FAQ

**Это отдельный Durable?** Нет, используются существующие Native owner/registry/scheduler/guards.

**Можно восемь агентов?** Roster проверен deterministic/faux; восемь живых моделей не запускались в приёмке и требуют разрешения.

**Настройка по GitHub полностью проверена на новой машине?** Нет. Проверены карта чтения, реальные команды и установленный локальный candidate; fresh-machine agent E2E остаётся отдельно.

**Где доказательства?** [Общий статус](project-status.md), [final review index](../evidence/native14/acceptance/final-review-index.json) и [план-отчёт](delivery-plan.md). Не переносите исторический HOST05 PASS на другой runtime.
