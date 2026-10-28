# DeLM для Pi Durable

**Несколько агентов, общая доска, один проект и один результат.** Агенты делят работу, публикуют готовые результаты и продолжают нужные беседы по событиям доски — без ручного переноса ответов между чатами.

Пакет содержит Python-доску, расширение, переносимый скилл и терминальный TUI **DeLM BOARD**. Сам Durable, модели и авторизация не поставляются: используются ваша установка и её настройки. Агенты открываются в обычных терминалах; определённый менеджер окон не нужен.

> **Совместимость:** текущий путь использует registry loader установленного Native 1.4 и его реальный trusted admission. Он проверяется на фактическом Native, а не на подменном host. Итоговая локальная приёмка установленного candidate завершена с двумя независимыми review и явной поправкой измерения удаления. Код опубликован; live reload команды и fresh-machine agent E2E не проверялись. [Статус и границы](docs/project-status.md). Совпадение версии SDK само по себе не означает совместимость. [Точный контракт](docs/native14-contract.md).

## Документация и итог работ

[Полная карта](docs/index.md) · [Что сделано](docs/project-status.md) · [План, задачи и хронология](docs/delivery-plan.md) · [Руководство пользователя](docs/user-guide.md) · [Руководство разработчика](docs/developer-guide.md) · [Compound-урок](docs/solutions/workflow-issues/completion-evidence-chain.md)

Текущие сводные статусы отделены от неизменных исторических отчётов. Итоговая [приёмка Native 1.4](docs/native14-acceptance.md) читается вместе с [final review index](evidence/native14/acceptance/final-review-index.json): исходный post-removal флаг отозван и заменён настоящим SDK witness. Документационные дополнения после опубликованного commit не считаются автоматически отправленными на GitHub.

## Настройка агентом по ссылке на GitHub

Передайте своему кодирующему агенту ссылку и запрос:

```text
Настрой DeLM из https://github.com/Diffuzmetall/pi-durable-delm
для моего текущего проекта и уже установленного Pi Durable.
Прочитай prompts/setup-delm.md и docs/agent-setup.md, затем выполни настройку.
Подключи скилл и расширение, открой поставляемый TUI DeLM BOARD.
Сохрани мои модели, авторизацию, настройки, guards и существующие беседы.
Без отдельного согласия не запускай платные модели. Подтверди, что реально работает;
при несовместимости назови blocker, не устанавливай другой Durable.
```

**[Полный готовый промпт](prompts/setup-delm.md)** · **[Карта настройки для агента](docs/agent-setup.md)**

Агент проверяет настоящий Native, устанавливает только DeLM, подключает скилл и расширение, выдаёт команды открытия агентов и проверяет результат. Если проект, план и разрешённый запуск уже заданы, новое интервью не нужно. Права доступа, число участников и расходы не угадываются.

## Что делает DeLM

| Без общей доски | С DeLM |
|---|---|
| Ответы переносят между отдельными чатами | Агенты читают общие задачи и связанные результаты |
| Владение задачей согласуют вручную | Атомарный claim с revision/generation fencing |
| Потребитель ждёт всю работу автора | Полезный ранний output завершается отдельно |
| Кто-то опрашивает агента «готово?» | Native watcher продолжает нужную беседу по событию |
| Доставку легко спутать с прочтением | Сохранённый snapshot → чтение → явный ACK |

Для маленького последовательного изменения достаточно одного агента. Команда полезна при независимых направлениях: например, контракт, реализация и интеграционные тесты. Поддерживаются roster 2/4/8; восемь fixture-identities не доказывают работу восьми живых моделей и не разрешают расходы.

## Как всё связано

![DeLM: существующий Native, точные сессии, actor CLI, общая доска и snapshot/read/ACK](docs/images/delm-architecture.svg)

[PNG](docs/images/delm-architecture.png) · [Редактируемый SVG](docs/images/delm-architecture.svg)

```text
Утверждённый запрос и план → скилл + launcher → точные Native sessions
                                                     ↕
                                        actor CLI → Python-доска
                                                     ↓ событие
                                            Native delm_wait
                                                     ↓
                                        snapshot → чтение → ACK
```

Доска владеет задачами, событиями и receipts. Native владеет беседами, моделями, scheduler и guards. Расширение работает внутри существующего владельца Native, использует его реальный admission и приватный Unix control socket; не создаёт второй Harness и не пишет напрямую в Native SQLite. Обычный shared `prompt` нельзя повторять как stable-ID input: его transport ID не обеспечивает эту гарантию.

## Требования

- POSIX-система, Python 3.10+ со stdlib `sqlite3`; для TUI — `curses` и интерактивный терминал.
- Уже установленный Native 1.4 с совместимым registry loader, реальным trusted admission и его matching SDK. Для текущего пути нужен Node ≥22.19.0; не смешивайте физические SDK разных версий.
- Разрешённый workspace, утверждённые инструкции и план. Живой запуск команды требует отдельного разрешения на модели и участников.

Установщик payload не скачивает зависимости и не меняет Native. При несовместимости агент сообщает точную причину; другой Durable или патч чужого host не служат автоматическим исправлением. Исторические Chord/session-facet assets сохранены отдельно, но не являются текущим способом подключения.

## Получить и установить пакет

Исходники доступны на GitHub; npm publish и готовый GitHub Release не подразумеваются. В новом каталоге:

```bash
git clone https://github.com/Diffuzmetall/pi-durable-delm.git
cd pi-durable-delm
export OUT="$(mktemp -d)"
npm pack --ignore-scripts --pack-destination "$OUT"
export ARCHIVE="$OUT/pi-durable-delm-0.1.0.tgz"
```

`npm pack` не устанавливает зависимости и не публикует пакет. Проверьте происхождение, commit и содержимое архива до исполнения его кода. Для пробы установите в пустой временный prefix:

```bash
export SANDBOX="$(mktemp -d)"
export PREFIX="$SANDBOX/install"
mkdir "$SANDBOX/bootstrap"
tar -xzf "$ARCHIVE" -C "$SANDBOX/bootstrap" package/packaging/install.py
python3 "$SANDBOX/bootstrap/package/packaging/install.py" install "$ARCHIVE" --prefix "$PREFIX"
export PACKAGE="$PREFIX/current"
"$PACKAGE/bin/delm" --help
```

Ожидается `status:installed`; повтор того же архива возвращает `unchanged`. `native_registered:false` означает именно установку payload, не загрузку расширения. Для постоянного использования выберите свой стабильный `PREFIX`.

## Попробовать доску без моделей

```bash
export DEMO="$(mktemp -d)"
mkdir "$DEMO/project"
export RUN="$DEMO/run"
"$PACKAGE/bin/delm" init "$RUN" \
  --shared-workspace "$DEMO/project" --n 2 --task 'Проверить общую доску'
"$PACKAGE/bin/delm" serve "$RUN"
```

Backend остаётся в foreground. Во втором терминале с тем же `RUN`:

```bash
"$RUN/alice/bin/context" domain '{"op":"projection"}'
python3 "$PACKAGE/scripts/delm_board.py" "$RUN" --observe
```

**TUI входит в пакет:** тот же экран `DeLM BOARD | READ ONLY` с AGENTS, TASKS и FACT/FAIL. Стрелки или `j`/`k` выбирают строку, Enter открывает детали, Tab переключает задачи/заметки, `/` ищет, `l` переводит фокус в журнал, `q` закрывает только observer. Он не перезапускает сервер/агентов и не читает/ACK-ает сообщения за модель.

Для текстового smoke есть `--once`; он не заменяет проверку интерактивного TUI. Backend останавливается через Ctrl+C в его терминале. Не делайте повторный `init` ради продолжения — используйте прежний RUN.

Небольшой независимый пример:

```bash
python3 -B -m unittest discover -s "$PACKAGE/examples/slugify" -v
python3 "$PACKAGE/examples/slugify/slugify.py" 'Привет, мир!'
# привет-мир
```

## Подключить скилл

Задайте `PROJECT` как существующий разрешённый workspace. Подключение project-local:

```bash
mkdir -p "$PROJECT/.pi/skills"
python3 -c 'import sys; from pathlib import Path; Path(sys.argv[2]).symlink_to(sys.argv[1], target_is_directory=True)' \
  "$PACKAGE/skills/delm" "$PROJECT/.pi/skills/delm"
```

Если запись уже существует, команда откажет, не заменяя файл/каталог/ссылку и не создавая вложенную ссылку. Не удаляйте чужой скилл. Обнаружение скилла Native проверяется отдельно: существующий worker мог закэшировать список.

Registry-расширение подключает actor launcher при `open`. Его не нужно передавать обычному Pi ExtensionAPI или регистрировать как старый Chord session facet. Существующие plugins и guards сохраняются.

## Запустить агентов в обычных терминалах

Задайте разрешённые абсолютные пути `PROJECT`, `PLAN`, `APPROVED_PROMPT`, `GLOBAL_AGENTS` и новый приватный `RUN` вне проекта. `GLOBAL_AGENTS` — существующий разрешённый файл правил, не личный config/auth.

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" prepare \
  --workspace "$PROJECT" --plan "$PLAN" --prompt-file "$APPROVED_PROMPT" \
  --global-agents "$GLOBAL_AGENTS" --agents 2 --run-dir "$RUN"
```

`prepare` сохраняет inputs и печатает команды backend, observer и `native_open_commands` для каждого actor. Процессы Native и модели ещё не запускаются.

1. Запустите напечатанную команду `serve` в одном терминале.
2. Откройте каждого actor в отдельном обычном интерактивном терминале:

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor alice
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor bob
```

`open` исполняет установленный `pi-durable` с фиксированными run/actor/adapter и свежим приватным endpoint. При необходимости `--native-executable FILE` указывает уже установленный executable. Launcher не задаёт другую модель, thinking, auth или глобальные настройки.

**Все участники открываются с MCP и встроенным CodeMode.** Пакет не добавляет `--no-mcp` и отказывает при отсутствии этих возможностей. Используется MCP-конфигурация Native: выключенные серверы остаются выключенными, а ошибки отдельных подключений нужно проверить через `/mcp` в самой панели.

CodeMode встроен в SDK и сам по себе не требует MCP-сервера. В целевом Native он регистрируется во время инициализации MCP — поэтому прежнее отключение этой ветки убирало и CodeMode. Если проект запрещает часть серверов, перед открытием используйте существующий Native-профиль `--mcp-server NAME --mcp-tools TOOL[,TOOL...]`; launcher сохранит его для exact reopening без изменения глобальных настроек. **[Подробности, безопасность и проверки](docs/mcp-and-codemode.md)**.

3. После готовности actor endpoints, при уже разрешённом model launch, в терминале настройки:

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" start --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" status --run-dir "$RUN"
python3 "$PACKAGE/scripts/delm_board.py" "$RUN" --observe
```

`start` подключается к уже открытым actors, записывает их настоящие identities и доставляет утверждённые inputs; **не создаёт окна или workers**. При неготовом endpoint повторите тот же start после его готовности, а не создавайте новый RUN. Процесс Native открыт — ещё не значит, что input принят.

## Продолжение, уведомление и остановка

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" notify --run-dir "$RUN" \
  --actor alice --input-file "$APPROVED_UPDATE" --request-id approved-update-001
python3 "$PACKAGE/skills/delm/Tools/Run.py" stop --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" resume --run-dir "$RUN"
```

`notify` требует новый утверждённый текст. При потере ответа повторяют **тот же ID и те же байты**; изменённый replay отвергается. Launcher не читает, не очищает и не отправляет editor draft.

`stop` останавливает собственные waiters и работу точных roots, не убивая терминалы и не удаляя историю. `resume` снимает stopped без dummy input. Остановка backend и выход из observer — отдельные действия.

Если Native действительно вышел, повторите прежнюю actor-команду `open`: она использует записанную точную `--session`, не общий `--continue`. Пока процесс жив, используйте его существующий терминал; второй владелец той же сессии запрещён. Не снимайте lock и не обещайте фоновую работу после закрытия обычного терминала. Потерянная identity незавершённого открытия требует reconciliation, не слепого повторного запуска.

[Полная справка](skills/delm/Tools/Run.help.md) · [Текущие операции](docs/native14-operations.md)

## Данные, update и удаление

| Место | Данные |
|---|---|
| Пакет | Код, скилл, prompts, TUI, tests и лицензии |
| Workspace | Общие исходники и результаты |
| Приватный RUN | Board, inputs, receipts, tokens и launch metadata |
| Хранилище Native | Беседы, принятые inputs, scheduler и guards |

Backup доски включает **`context.sqlite` и `context-bodies.sqlite`**. Не публикуйте RUN, токены, Native SQLite или личные беседы. Readiness требует всех точных DONE; FAIL/correction — повод переоценить, не успешная готовность. Файловые leases advisory, не OS-lock; TTL не доказывает смерть writer.

Перед удалением остановите собственную работу, закройте observer/backend и отключите только DeLM при безопасном lifecycle Native. Сохраните другие plugins/guards, проверьте target своей skill symlink и уберите только её. Затем:

```bash
python3 "$SANDBOX/bootstrap/package/packaging/install.py" uninstall --prefix "$PREFIX"
```

Изменённые или неизвестные version trees сохраняются в `retained`; RUN, проект и Native sessions не удаляются. Update — `install` другого проверенного архива; rollback — `rollback --prefix "$PREFIX"`. Они требуют чистых управляемых деревьев и согласованного lifecycle активных watchers. [Подробности payload lifecycle](docs/operations.md).

## Диагностика и доказательства

| Симптом | Что проверить |
|---|---|
| Нет trusted admission/совместимого registry | Контракт фактического Native; не подменять host или policy |
| Actor endpoint не готов | Правильные RUN/actor, работающий `open`, private socket и первую ошибку Native |
| Другой процесс владеет сессией | Вернуться к его терминалу; не удалять lock и не создавать замену |
| `STALE` / scope / approval mismatch | Прочитать текущие identities/revision/generation и сверить сохранённые bytes |
| Не пришёл wake / receipt pending | Все точные DONE, relevant FAIL и реальный snapshot/read/ACK |
| Skill symlink уже существует | Проверить владельца и target, не перезаписывать чужое |

Bug report: commit/version, OS, artifact hash, точная команда, exit code и маленький синтетический пример — без secrets и дампов бесед.

Текущие реальные Native1.4 проверки различают model-only faux и настоящие owner/tools/guards/storage/board: [baseline](docs/native14-fixture.md), [интеграция доски/reopen/readACK](docs/evidence/native14/fixture-integration/result.json), [запуск без менеджера терминалов](docs/native14-packaging.md#actual-no-multiplexer-runtime-proof), [упаковка](docs/native14-packaging.md). Финальный установленный candidate и интерактивный TUI приняты отдельно: [итоговый индекс](evidence/native14/acceptance/final-review-index.json) связывает точные fingerprints, обе независимые рецензии и поправку измерения. Одного PASS компонента для всего продукта недостаточно.

Исторические [HOST05](docs/user-host-acceptance.md) и [принятый r2 manifest](docs/evidence/user-host/accepted-r2-manifest.json) относятся к другому публичному host 1.0.2 с API-патчем. Они сохранены, но не доказывают совместимость текущего 1.4. Живые модели, восемь живых агентов, Windows и произвольные будущие миграции не объявлены проверенными.

## Происхождение и лицензия

Основа — [Decentralized Multi-Agent Systems with Shared Context](https://arxiv.org/abs/2606.10662v3), Mao et al., и [Python DeLM](https://github.com/yuzhenmao/DeLM), commit `66617616e708758f91624e5cc03659732b82f6a6`. Это адаптация для Native Pi Durable, не официальный продукт авторов исследования. Результаты статьи не превращаются в обещания ускорения или качества моделей.

Наш код — [MIT](LICENSE). [Исходный DeLM MIT notice](vendor/DeLM/LICENSE), [Native notice для исторического API-патча](LICENSES/pi-native.txt) и [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) сохранены. Другой [delm-agent-plugin](https://github.com/Decentralized-LM/delm-agent-plugin) и его Rust runtime/private-worktree архитектура не поставляются.

[Архитектура](docs/architecture.md) · [Контракт доски](docs/DeLM-domain-protocol.md) · [Настройка агентом](docs/agent-setup.md) · [UPSTREAM](UPSTREAM.md) · [Provenance](provenance.json)
