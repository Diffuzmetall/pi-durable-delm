# HOST-04-NATIVE: реальный DeLM в существующем Native Durable

## Вердикт и границы

**PASS: независимый deterministic real-host сценарий DeLM выполнен.** Это результат HOST-04-NATIVE, не финальная приёмка установленного архива, launcher или всех файлов продукта. HOST-05 отдельно проверяет конечный пакет; Alice/Carol независимо проверяют эту fixture, автор её не самопринимает.

Продукт — только **DeLM plugin + Python board/CLI/skill**, подключаемый к существующему пользовательскому Durable. Не поставляются Native host/framework/runtime, замещающий Harness, личный wrapper или модели автора. Normal quickstart не должен требовать скачивания либо пересборки тестового host.

Публичный Native source snapshot применяется **только как тестовый стенд вне артефакта**, с отдельными HOME/project/data. Проверенный pin: Pi v1.0.2, `cd32f7725fdbddbaecdff5b1e68491563394e0ca`, плюс явно обозначенный трёхфайловый API patch. Это не утверждение о stock v1.0.2 или ordinary Pi CLI 1.4.0. Отсутствующий в пользовательском host capability должен диагностироваться явно, не заменяться автоматической установкой другого host. Pocket отвергнут пользователем и остаётся только историей исследования альтернатив.

## Минимальный API prerequisite

`extensions/delm/public-host-api.patch`, SHA256 `3460016c2130e2286ccd59c522b4318a2c13b0ad034dbb09f4e31776b23098ae`, даёт разрешённым session facets LOCAL-only `DurableSession.get(context)`: существующие registry/Harness/root и настоящие session ID/cwd/SQLite path. Новый владелец storage не создаётся, scheduler и инструменты Native остаются прежними. Удалённый вызов capability запрещён самим сервером.

Patch применён только к одноразовой тестовой копии публичного source. Сохранены preimages, postimage hashes, точная версия и успешные dry-run/apply logs: [api-patch.json](../tests/host/evidence/native-delm/api-patch.json). Рабочая установка автора не менялась. Отдельная исходная baseline fixture сохранена неизменённой.

## Настоящая загрузка, не подмена host

Официальный Native server запущен с реальным DeLM package path. Его собственный loader читает **настоящий product package.json**, собирает Chord bundle и загружает `session-facet.js` в два собственных session workers. Финальные проверки не используют сгенерированный вместо product manifest или собственный Harness.

В обоих workers реальный `delm.control.identity` вернул правильные canonical workspace/session path, root conversation 1, разные session IDs и разные persistent instance IDs. Клиент намеренно объявил `pi.durable-session` без `local:true`, чтобы не полагаться на клиентский запрет: настоящий сервер отказал в RPC. Обычный Native AgentController после этого продолжал работать. [Результат loader/control](../tests/host/evidence/native-delm/delm-plugin-result.json), [проверенный candidate](../tests/host/evidence/native-delm/delm-package-candidate.json).

## Сквозной сценарий: 24 deterministic HTTP requests

Полный текущий результат: [board-e2e/result.json](../tests/host/evidence/native-delm/board-e2e/result.json). Все модели заменены только на локальный HTTP provider; host, discovery, admission, scheduler, инструменты, Python HTTP/CLI и storage настоящие. Живых LLM/платных запросов — **0**.

1. Два настоящих Native workers связываются с alice/bob, одной рабочей папкой и новой настоящей DeLM-доской. Фиксируются exact session/instance bindings.
2. Модель bob вызывает настоящий `delm_wait` на двух зависимостях. Они заранее claimed разными fixture actors, чтобы ownership-change reevaluation не смешивался с проверкой ALL-DONE. Реальные actor CLI claim request затем воспроизводятся теми же стабильными IDs через Native bash tool.
3. Официальный Native server и workers штатно завершаются. После нового старта с тем же server UUID открываются **прежние** session IDs/paths/instance IDs; прежний waiter ID остаётся waiting. Повтор approved input возвращает replay, модель повторно не запускается.
4. В настоящем Native CLI client/OS PTY на bob вводится несданный draft, **без Enter**. В сценарии выполняется реальный Native profile reload, затем producer Native bash пишет общий результат и завершает первый output. В 400 ms наблюдении частичный DONE не возобновляет exact wait.
5. После второго DONE событие доски возобновляет именно bob. Его модель выполняет настоящий actor CLI: pending → сохранённый snapshot → чтение требуемых DONE → explicit ACK. Настоящий `delm_wait(status)` подтверждает native state `sent`, `acked:true`, `deliveryState:acked`.
6. На реальном TUI одновременно видны новый `NATIVE_WAKE_ACKED` и сохранённый draft. В реальных Transcript services **обоих** conversations draft отсутствует; лишнего model request нет.
7. Отдельный настоящий `work` wait получает hint после создания новой READY задачи. Модель читает/ACK её receipt; задача остаётся open/unowned, wake не назначает владельца и не выставляет DONE.
8. Следующий exact wait явно отменяется настоящим tool call. Позднейший FACT не возобновляет отменённое ожидание и не превращает задачу в DONE.
9. Дополнительная реальная owner policy, установленная в тот же registry **до DeLM binding**, блокирует модельный `delm_wait` через настоящий `ToolTask.beforeTool`. После install/restart/reload hook сохранился: один отказ с `FIXTURE_EXISTING_OWNER_POLICY_DENIED`, denial присутствует в Native history, новый waiter не создан.

Дополнительная policy — обычный Native plugin **только тестового владельца**, не mock admission, не продуктовый host и не approval stub. Она проверяет сохранность настоящего механизма hooks.

## Проверенные негативные случаи и lifecycle

| Проверка | Результат |
|---|---|
| Same request ID + те же approved bytes | PASS: replay, без повторной генерации |
| Same ID + изменённый approved payload либо input type | PASS: отказ |
| Неверные session, workspace, instance после успешного bind/status | PASS: отказ |
| Перепривязка существующей session к другому actor | PASS: отказ, исходный actor сохранён |
| Stop → новый input | PASS: отказ |
| Resume | PASS: stopped сброшен, dummy/editor input не отправлен |
| Pending waiter через server/worker restart | PASS: те же IDs/instance/waiter, последующая доставка одна |
| Настоящий Native profile reload | PASS: новый test-policy bundle v2, прежний DeLM waiter и identity сохранены |
| Editor draft при reload и настоящем DeLM wake | PASS: остался на экране, в Native histories не попал |
| Existing owner beforeTool policy | PASS: реальный native denial, hook не стёрт |
| Конечные процессы | PASS: штатные Native server и TUI exit 0 |

Reload использует ту же пару, что официальный `/reload`: `PresentationPlugins.reload` собирает profile, затем `SessionPlugins.reload` обновляет worker. Для подтверждения реальной замены меняется **только тестовый policy plugin** v1→v2 в приватной fixture; DeLM runtime bytes остаются неизменными. Это не тест обновления архива DeLM на новую версию — такой update/rollback относится к HOST-05.

Доказательства: [arm-client.log](../tests/host/evidence/native-delm/board-e2e/arm-client.log), [finish-client.log](../tests/host/evidence/native-delm/board-e2e/finish-client.log), [restarted-server.log](../tests/host/evidence/native-delm/board-e2e/restarted-server.log), [экран до DeLM wake](../tests/host/evidence/native-delm/board-e2e/tui/before-DeLM-wake.txt), [экран после](../tests/host/evidence/native-delm/board-e2e/tui/after-DeLM-wake.txt), [реальные terminal bytes](../tests/host/evidence/native-delm/board-e2e/tui/tui-transcript.log). Экран декодирует существующий публичный xterm-based upstream VirtualTerminal, не самописный ANSI parser.

## Прежние и неудачные проверки

Исходная unmodified Native baseline отдельно подтверждает два workers, официальный example facet, restart/history и настоящий editor под внешним Native input. После переиспользования PTY helper её повторная проверка прошла с 3 deterministic HTTP requests: [native-repro/native-draft/result.json](../tests/host/evidence/native-repro/native-draft/result.json). Это не подменяет описанный выше DeLM-event тест.

Первый loader failure назвал facet ID invalid. Причина была не в строке ID: публичный loader читает default export, а не named `facets`. Bob добавил default export, затем настоящий attach/identity прошёл; FAIL закрыт на доске в 670. Прежние logs сохранены.

Другие собственные fixture failures сохранены: отсутствующий `control.js` при ранней staging-копии; ожидание приватного error text вместо публичного `ServerError.code=internal_error`; op:create без обязательного detail; вызов только presentation build без worker reload. Финальный тест использует настоящий product manifest, полную официальную reload-пару и публичную wire-семантику; guards не ослаблены.

Unit/safety checks fixture: **6/6 PASS**, [fixture-unit-final.log](../tests/host/evidence/native-delm/fixture-unit-final.log). Старые промежуточные 9/11-request результаты сохранены в board-e2e и не выдаются за конечный 24-request candidate.

## Повторение только для разработчика тестов

Это **не инструкция установки пользовательского Durable**. На уже подготовленной независимой публичной Native fixture с тремя проверенными API changes:

```bash
python3 -B tests/host/smoke_native_delm.py --fixture "$PRIVATE_TEST_FIXTURE"
python3 -B tests/host/smoke_native_board.py --fixture "$PRIVATE_TEST_FIXTURE"
python3 -B -m unittest discover -s tests/host -p 'test_*.py' -v
```

Locator и host source лежат вне package. Использованы только существующие публичные dependencies read-only; для PTY test нужен уже установленный `@xterm/headless`. Никаких новых установок, авторских credentials/config/conversations, global settings или прямого SQL в Native DB. Все session/history операции идут через настоящего owner, публичные services и его SDK. Истории собственных test sessions сохраняются для воспроизведения.

## Что остаётся HOST-05

**NOT_YET_TESTED этим отчётом:** конечный архив, установленный payload, пользовательский normal launcher без source-host prerequisite, update/rollback/disable/uninstall с сохранением user data; полный конечный package/provenance regression и независимая проверка fixture Alice/Carol. Пройденный Native core E2E не разрешает commit/push/publication, live-model smoke или замену действующего host.
