# DeLM для Pi Durable

DeLM помогает нескольким агентам работать над одной задачей в общем проекте. Они берут работу с общей доски, рано делятся полезными результатами и собирают один проверенный результат. Вам не приходится вручную переносить ответы между участниками.

Пакет объединяет Python-доску, Native extension, скилл подготовки и запуска, observer и примеры. Он полезен, когда в задаче есть независимые направления; для одного небольшого изменения отдельный агент обычно проще. Скилл помогает выбрать **2, 4 или 8** участников по полезной работе, а не по числу файлов.

## Пример задачи

«Добавить Unicode-slugify без сторонних зависимостей. Сохранить буквы и цифры разных алфавитов, проверить кириллицу, пробелы и пустую строку». Один участник пишет функцию, второй — тесты; оба работают в одной папке и публикуют доказательства на доске.

```text
Пользователь → утверждённый план → общая доска ↔ участники
                                       ↓
                               один общий результат
```

Это адаптация идеи DeLM для Native Pi Durable, **не официальный продукт авторов исследования**. Мы не переносим показатели скорости/качества из статьи в обещания этого пакета.

## Статус и требования

**Публичные исходники под MIT: [Diffuzmetall/pi-durable-delm](https://github.com/Diffuzmetall/pi-durable-delm). Это не production-релиз Native.** Production-запуск команды Native пока ограничен публичным admission/control API: наличие SDK само по себе не доказывает совместимость host. Прямой `submit`, разрешающая заглушка и FauxHost не заменяют защищённый ввод. Не устанавливайте приватный host и не отключайте guards ради запуска. Python-доску можно использовать отдельно.

Нужны Python 3 со stdlib `sqlite3` и `curses` для терминального UI; для SDK-компонента — Node ≥22.19.0 и публичные `@earendil-works/pi-durable`, `pi-ai`, `chord` версии 1.4.0. Reload-тест использует `jiti` 2.7.0. Tern нужен только для автоматических панелей, его не устанавливают молча. Авторизация и выбранная модель принадлежат пользователю Native, а не пакету. Проверенные версии и новые результаты артефакта фиксируются в [чистой приёмке](docs/acceptance.md); старые результаты исходной папки сюда не переносятся.

## Установить локальную поставку

Это установка автономного **payload**, не регистрация защищённого Native-плагина. Python-ядро работает без Node dependencies; публичный SDK нужен отдельно для Native-компонента и его тестов. Подтверждённого универсального Native install пока нет: [точный API gate](docs/native-compatibility.md).

Для сборки из этой папки нужен уже установленный npm. Команда не устанавливает зависимости и не публикует пакет:

```bash
export OUT="$(mktemp -d)"
npm pack --ignore-scripts --pack-destination "$OUT"
export ARCHIVE="$OUT/pi-durable-delm-0.1.0.tgz"
```

Если готовый архив уже получен, задайте `ARCHIVE` его абсолютным путём вместо сборки. Просмотрите происхождение и содержимое перед запуском установщика. Для первой пробы используйте пустой временный каталог:

```bash
export SANDBOX="$(mktemp -d)"
export PREFIX="$SANDBOX/install"
mkdir "$SANDBOX/bootstrap"
tar -xzf "$ARCHIVE" -C "$SANDBOX/bootstrap" package/packaging/install.py
python3 "$SANDBOX/bootstrap/package/packaging/install.py" install "$ARCHIVE" --prefix "$PREFIX"
export PACKAGE="$PREFIX/current"
"$PACKAGE/bin/delm" --help
```

Признаки успеха: JSON `status:installed`, повтор той же install-команды даёт `unchanged`; `native_registered:false` честно сообщает, что Native не зарегистрирован. Пакет полностью лежит под prefix, без ссылок на исходный проект. В payload включены skill, extension, Python, vendor/license, templates, tests и demo.

Skill discovery path для обычного Pi — `skills/delm`; его наличие в payload не подтверждает обнаружение конкретным Native Durable. Нельзя подставить SDK-adapter вместо обычного Pi ExtensionAPI. Наши части распространяются под [MIT](LICENSE) по решению владельца. `private:true` сохранён как защита от случайного npm publish; публичному GitHub-репозиторию это не мешает. MIT notice включённого upstream сохранён отдельно.

## Как попробовать ядро без моделей

Из корня установленного пакета:

```bash
cd "$PACKAGE"
python3 scripts/delm_local.py --help
```

Создайте временный проект и приватный RUN **вне** его рабочей папки:

```bash
export DEMO="$(mktemp -d)"
mkdir "$DEMO/project"
export RUN="$DEMO/run"
python3 scripts/delm_local.py init "$RUN" \
  --shared-workspace "$DEMO/project" --n 2 \
  --task 'Создать Unicode-slugify и проверить его без сторонних зависимостей'
python3 scripts/delm_local.py serve "$RUN"
```

Последняя команда держит backend в foreground; оставьте терминал открытым. В другом терминале задайте `RUN` напечатанным путём и из корня пакета выполните:

```bash
python3 scripts/delm_board.py "$RUN" --once
"$RUN/alice/bin/context" domain --help
"$RUN/alice/bin/context" domain '{"op":"projection"}'
python3 scripts/delm_board.py "$RUN" --observe
```

Признаки успеха: init создал bound CLI двух участников; backend слушает локальный endpoint; projection показывает actor roster и пустую очередь; observer открывается отдельно. Выход `q` закрывает только observer. Остановите foreground backend через Ctrl+C. **Это проверка Python/CLI, не стартовая доставка Native и не работа живых моделей.** Не отправляйте пробный input в свои беседы ради такого smoke test.

## Выполнить Unicode-demo

Из корня установленного пакета:

```bash
python3 -B -m unittest discover -s examples/slugify -v
python3 examples/slugify/slugify.py 'Привет, мир!'
```

Ожидается проходящий unittest и `привет-мир`. Это детерминированный пример результата, не benchmark и не имитация модели. [План примера](examples/slugify/PLAN.md) делит реализацию и тесты между двумя участниками общего проекта.

## Подготовить, запустить и продолжить команду

Сначала без сервисов проверьте доступные возможности:

```bash
python3 skills/delm/Tools/Run.py capabilities
```

Для подготовки скопируйте маленький demo в новый проект, создайте файл с собственным утверждённым запросом и задайте `GLOBAL_AGENTS` реальным разрешённым путём глобальных правил. Не заменяйте отсутствующий файл фиктивным «прочитал». Команда использует выбранный план, без нового интервью:

```bash
python3 skills/delm/Tools/Run.py prepare \
  --workspace "$PROJECT" --plan "$PROJECT/PLAN.md" \
  --prompt-file "$APPROVED_PROMPT" --global-agents "$GLOBAL_AGENTS" \
  --agents 2 --run-dir "$NEW_RUN"
python3 skills/delm/Tools/Run.py status --run-dir "$NEW_RUN"
```

`PROJECT` должен существовать и содержать AGENTS/PLAN; `APPROVED_PROMPT` и `GLOBAL_AGENTS` — существующие разрешённые файлы; `NEW_RUN` — новый приватный путь вне проекта. Можно повторять `--reference FILE` для разрешённых inputs. Prepare сохраняет точный текст и hashes, создаёт bindings и печатает argv отдельных backend/observer; ничего не запускает. До старта backend status честно покажет, что он недоступен. После запуска напечатанного `serve` повторный status читает реальный HTTP projection.

**Автоматические `start`, `resume`, `notify`, `stop` сейчас отказывают до побочных эффектов:** production host-control API не подтверждён. Это известное ограничение, не готовая команда живого запуска. [Полная справка launcher](skills/delm/Tools/Run.help.md) и [совместимость](docs/native-compatibility.md).

Скилл `delm` должен прочитать полностью разрешённые global/project AGENTS, исходный запрос, готовый план и references. Готовый план используют без повторного интервью; уточняют лишь реальные пробелы. Команды живого запуска допустимы только после прохождения capability gate host и явного разрешения на модели.

- **2:** небольшой объём полезной независимой работы.
- **4:** четыре направления с разделёнными областями записи.
- **8:** восемь направлений, ресурсы и разрешение. Fixture identities не равны восьми живым LLM.

Один запуск сохраняет исходный утверждённый запрос, план, frozen WORKER, actor START и фактический первый input. Создание prompt-файла не доказывает принятие Native. После неопределённой доставки сверяют прежний request/marker, а не создают второй run.

Продолжение использует **точную session identity**, не shared-cwd `--continue`. Новый комментарий, ответ на вопрос и разрешение на действие не смешиваются. Перед reopening сохраните несданный editor draft штатно, не отправляя его. Если публичный host не предоставляет нужного control/stop API, ограничение сообщается прямо, без фиктивной команды.

## Где находятся код и история

Код пакета лежит в `scripts/`, `extensions/delm/`, `skills/delm/`, `vendor/DeLM/`. Результат работы находится в проекте пользователя. Приватный RUN хранит задачи, публикации, receipts, вложения и launch metadata; беседы и scheduler отдельно принадлежат Native.

Доска логически одна, но её backup включает **context.sqlite и context-bodies.sqlite**. Не публикуйте RUN, `config.json`, токены и Native sessions. Удаление или обновление пакета не должно удалять историю или чужие изменения. Подробная [схема хранения](docs/architecture.md).

## Что означают ожидания, ошибки и бронь

**«Нужен результат»** — exact wait по UUID: готовы должны быть все названные задачи. Связанный FAIL или ended producer может разбудить для разбора, но не объявляет результат готовым.

**«Готов взять работу»** — work wait без списка задач. Это hint, не назначение: участник читает доску и выигрывает claim. Если весь план закончен, он завершает поручение, а не ждёт дополнений.

Короткое уведомление Native — ссылка на полный snapshot, не подтверждение его чтения. Участник воспроизводит сохранённый снимок, читает и явно ACK; непрочитанное остаётся pending. Старый ответ не даёт разрешения перезаписать переданную задачу.

Бронь путей и ресурсов **advisory**, не OS-lock. Она не останавливает произвольный shell writer; TTL не доказывает его смерть. Связанный FAIL блокирует затронутый результат до явного исправления с доказательствами, а не всю независимую работу.

Контракты: [CLI и доска](docs/DeLM-domain-protocol.md), [exact/work и доставка](docs/DeLM-native-protocol.md).

## Остановка, обновление и откат

Backend, observer и участники останавливаются отдельно. `q` observer не останавливает backend или модели. Foreground backend завершается Ctrl+C; detached-процесс сначала идентифицируют по точному PID/argv/RUN. Нельзя использовать `pkill python`, удалять lock-файлы или объявлять writers остановленными по закрытому окну.

Перед обновлением сохраните artifact и backup данных, проверьте hashes управляемых файлов. Чужие изменения не перезаписывают. Uninstall по умолчанию сохраняет RUN и беседы. **Перед downgrade к версии без work дренируйте/отмените work-watchers в новой версии:** старая может принять пустой items за «все зависимости DONE». Историю не стирают ради отката.

Операции локального payload из любого каталога, пока сохранён bootstrap:

```bash
python3 "$SANDBOX/bootstrap/package/packaging/install.py" install "$ARCHIVE" --prefix "$PREFIX"
python3 "$SANDBOX/bootstrap/package/packaging/install.py" rollback --prefix "$PREFIX"
python3 "$SANDBOX/bootstrap/package/packaging/install.py" uninstall --prefix "$PREFIX"
```

Install нового архива — update; rollback требует **двух** чистых управляемых версий. После первой или повторной установки того же архива откатывать ещё нечего. Изменённый/дополненный payload заставляет update/rollback отказать; uninstall сохраняет такие деревья и перечисляет их в `retained`, не удаляя чужие файлы. Удаление пакета не означает остановку уже работающих процессов: сначала завершите их штатно. Не запускайте rollback до дренирования work-watchers.

Порядок safe stop, backup, rollback, клавиши observer и типичные ошибки: [operations.md](docs/operations.md).

## Происхождение и права

| Часть | Происхождение и отличие |
|---|---|
| ProtectedBoard, события, HTTP handler, исходный CLI | Закреплённый Python DeLM; включён с полным MIT notice |
| Shared checkout, domain/delivery/leases, observer | Наша адаптация: один общий результат вместо отдельных полных решений |
| Native wait/work и компактная доставка | Наш компонент поверх SDK; production admission требует отдельного host-контракта |
| Скилл, launcher и упаковка | Переносимые инструменты адаптации; без личной конфигурации автора |

Исследование: [Decentralized Multi-Agent Systems with Shared Context, v3](https://arxiv.org/abs/2606.10662v3), Mao et al.; [сайт](https://yuzhenmao.github.io/DeLM/), [Python source](https://github.com/yuzhenmao/DeLM), commit `66617616e708758f91624e5cc03659732b82f6a6`. Полная [MIT-лицензия upstream](vendor/DeLM/LICENSE) включена в пакет.

Отдельный [продуктовый плагин DeLM](https://github.com/Decentralized-LM/delm-agent-plugin) использует другую архитектуру; его Rust runtime, Codex hooks и два private worktrees не выдаются за возможности этого пакета. Подробности: [UPSTREAM](UPSTREAM.md), [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md), [provenance.json](provenance.json), [parity.json](parity.json).

Владелец разрешил публикацию исходников в `Diffuzmetall/pi-durable-delm` под [MIT](LICENSE), создание Git-репозитория, commit и push. npm publish, GitHub Release и production-совместимость Native этой публикацией не заявляются. Историческая приёмка и исключённые локальные архивы описаны в [release-readiness.md](release-readiness.md).

## Ограничения и сообщения об ошибках

Python/HTTP, SDK/faux, discovery и production admission проверяются раздельно. Нет обещания ускорения моделей, справедливого распределения работы, физической блокировки файлов или поддержки любого Native host. Legacy isolated-режим сохранён отдельно; правила apply не применяются к shared checkout.

Для bug report нужны версии, OS, artifact hash, точная команда, exit code и маленький фиктивный пример. Не прикладывайте secrets, личные беседы, SQLite, traces или RUN целиком. [Безопасная диагностика](docs/operations.md#безопасный-bug-report).
