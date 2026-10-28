# MCP и встроенный CodeMode в Native 1.4

## Что изменилось в DeLM

Все production-участники открываются с MCP и встроенным CodeMode установленного Native. Launcher больше не добавляет `--no-mcp`. Перед созданием DeLM control расширение проверяет наличие Native MCP registry и инструмента `codemode`; без них запуск завершается понятной ошибкой, а не урезанной работой.

Это изменение launcher, скилла и контракта пакета. Оно не устанавливает другой Native, не меняет ваши модели/auth/settings и не превращает уже работающий процесс в MCP-enabled автоматически.

## CodeMode — не MCP-сервер

В оригинальном SDK 1.4 есть самостоятельный модуль:

```js
import { createCodemodeExtension } from '@earendil-works/pi-durable/codemode';
import { CodemodeSandbox } from '@earendil-works/pi-codemode';

const codemode = createCodemodeExtension({ sandbox: new CodemodeSandbox() });
```

Его можно зарегистрировать без MCP-клиента. Скрипт исполняется в QuickJS и вызывает доступные Native tools. Встроенный Durable CodeMode сохраняет журнал выполнения и использует Native nested calls для восстановления. Сам SDK не требует MCP-сервер для вызова локального `read` или `bash`.

Но приложение должно **зарегистрировать** модуль. Текущий целевой Native сначала устанавливает базовые coding tools (`read`, `write`, `edit`, `bash`), а встроенный CodeMode подключает в ветке инициализации MCP. Его `createMultiMcpCodemodeExtension` вызывает тот же оригинальный `createCodemodeExtension` SDK, добавляя зарегистрированные MCP tools и свои проверки доступа.

```text
Установленный Native
  ├─ базовые Native tools
  └─ инициализация MCP
       ├─ соединения с разрешёнными серверами
       ├─ их инструменты в Native registry
       └─ встроенный SDK CodeMode → вызовы доступных Native/MCP tools
```

Поэтому прежний флаг DeLM `--no-mcp` пропускал всю эту ветку и заодно лишал участников CodeMode. Это особенность подключения в целевом приложении, **не архитектурная зависимость самого CodeMode от MCP**. Новый runtime, дополнительный Harness или собственная реализация JavaScript для исправления не нужны.

## Какие серверы подключатся

Обычный `open` использует Native по умолчанию: подключаются серверы, включённые в пользовательской MCP-конфигурации. Выключенные серверы не включаются обратно. Наличие MCP-модуля не доказывает, что каждый сервер здоров: ошибки auth/transport могут остаться у отдельных подключений.

Реальное состояние смотрят командой `/mcp` в соответствующей Native-сессии. При обычной конфигурации доступен `mcp_status`; список основного чата не доказывает состояние отдельного участника.

Если проект запрещает некоторые серверы, выбрать профиль нужно **до открытия**. Пакет поддерживает существующие флаги Native, например для уже настроенного context-mode:

```bash
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor alice \
  --mcp-server context-mode --mcp-tools ctx_search
```

Это не новая система конфигурации: флаги передаются установленному Native. Выбранный actor profile сохраняется в launch metadata и повторяется при точном reopening без повторного указания. В explicit single-server режиме действуют ограничения Native на инструменты и его MCP-авторизация. Подключён ровно выбранный сервер, не все остальные настроенные серверы.

Default startup может автоматически инициализировать identity включённого Agent Mail. Если проект запрещает такие подключения/регистрации, не запускать default profile в обход правил: выбрать разрешённый explicit profile. Пакет не редактирует глобальный MCP config и не снимает project restrictions ради зелёного smoke.

MCP нужен для разрешённых инструментов, но не заменяет доску: координация остаётся только через actor `context` и `delm_wait`. Возможность вызвать cloud/MCP tool не даёт разрешения на deployment, production writes, расходы или дополнительные модели.

## Обновление работающих сессий

Соединения MCP принадлежат Native-процессу и создаются при startup. `/reload` обновляет registry adapters, но не перестраивает MCP connections. После обновления пакета:

1. Сверить текущие project restrictions и старые frozen WORKER/START — они не переписываются молча.
2. Штатно остановить свою работу через `Run.py stop`; сохранить черновики.
3. Закрыть свой Native через `/quit` и открыть **ту же** записанную session через `Run.py open`.
4. Проверить `/mcp` и настоящий вызов `codemode` с nested tool result.

Не использовать `--continue` для нескольких участников одного cwd, не удалять lock, не создавать replacement session и не передавать повторно успешный bootstrap. Наличие файла новой версии не означает, что старый процесс уже загрузил MCP.

## Проверки

- SDK unit показывает регистрацию оригинального CodeMode без MCP-клиента.
- Production adapter отказывает без Native MCP и отдельно без CodeMode.
- Launcher units проверяют MCP-on, все четыре actors, сохранение explicit profile и точный `--session` при reopening.
- Installed-Native probe выполняет реальный CodeMode → локальный read → настоящий stdio MCP echo, затем проверяет replay, потерянный ответ, draft, stop/resume и exact reopening. Подменена только модель; это не live-model evidence.
- Живой smoke должен дополнительно подтвердить исполнение CodeMode моделью в каждой разрешённой панели. JavaScript через Bash и наличие имени в списке инструментов не заменяют этот тест.

Старые evidence с MCP-off остаются историей. Они не переписываются как будто исходный запуск уже был MCP-on. Новые результаты и ограничения публикуются отдельно.

[Scoped review и evidence от 2026-10-28](mcp-codemode-verification.md): настоящий live CodeMode/read/MCP stats подтверждён у Alice/Bob/Carol — **3/4**, не 4/4. Dave исключён из этой тройной проверки из-за черновика при handoff; последующие сообщения доски о reopening не подтверждают восстановление черновика. Первый search завершился ошибкой пустой KB; поисковый PASS не заявляется. Final installed-artifact acceptance остаётся отдельным pending gate.
