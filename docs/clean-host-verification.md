# HOST-04: независимый настоящий публичный host

## Текущий результат

**Среда настоящего публичного host готова и работает. Это ещё не финальная DeLM-приёмка.** На неизменённом Pi Pocket 0.14.0 проверены настоящий launcher, HTTP authentication, обнаружение и включение drop-in владельцем, два разных разговора в одной рабочей папке и реальный вызов инструмента через deterministic model provider.

Ни host, ни discovery, ни admission не подменены mock. Fixture не создаёт Harness и не открывает SQLite: единственный владелец — собственный production-код публичного host. Поддельна только **модель**: локальный OpenAI-compatible HTTP server выдаёт заранее заданные ответы. Платные/живые LLM не вызываются.

Сценарий `DeLM claim → результат → board event → wake → snapshot/read/ACK`, полные wrong-binding/replay/cancel/restart/draft/uninstall критерии и независимая проверка самой fixture относятся к следующему интеграционному этапу HOST-05. Не следует выдавать работоспособность clock-примера за готовность продукта DeLM.

## Проверенные публичные дистрибутивы

| Дистрибутив | Pin и фактический результат |
|---|---|
| Ordinary Pi CLI 1.4.0 | Публичный npm CLI не содержит experimental Durable host; обычный ExtensionAPI не равен Durable registry |
| Official Pi source v1.0.2 | `cd32f7725fdbddbaecdff5b1e68491563394e0ca`; настоящий experimental server/client/session-worker запущен и проверен на двух worker sessions |
| Pi Pocket v0.14.0 | `e5456a832d47e7154faf04320dd7602ae5051bf7`; настоящий CLI, owner authentication и drop-in tool проверены на двух разговорах |
| Pocket SDK peers | pi-durable/pi-ai/chord 1.1.0; jiti 2.7.0; версии проверены до старта |
| Среда теста | Linux x86_64, Node 24.19.0, Python 3.13.7 |

Исходники получены заново по публичному immutable commit через GitHub codeload, а не скопированы из личного host. Для Pocket использован архив SHA256 `3cccf81ccfee4a99420f6ff9140a43de98538f9d1778285ed454414c45259706`, **381 исходный файл**. Hash каждого файла сохранён в [источниках fixture](../tests/host/evidence/pocket-source.json).

Свежая папка содержит отдельные HOME, config/data и workspace. Переиспользовано только уже установленное публичное дерево npm dependencies с проверенными версиями; оно доступно read-only через symlink `node_modules`. Исходники, настройки и процессы личной установки не запускались и не менялись. Новые зависимости не устанавливались.

## Настоящий Pocket: выполненный сценарий

1. Запущен официальный `bin/pi-pocket.js --access local --cwd PROJECT --data DATA --port PORT` из свежего публичного snapshot. Сервер слушал только `127.0.0.1`.
2. Владелец вошёл через настоящий `/login`; cookie сохранился только в памяти тестового HTTP client. Новая owner-ссылка не публиковалась, token в логах заменён на `<REDACTED>`. Без cookie настоящий `/api/sessions` ответил **401**.
3. Официальный `docs/examples/clock.ts` помещён в изолированную `DATA/extensions/fixture-clock.ts`. Реальный loader обнаружил его **выключенным**. Владелец включил его через `/api/extensions/fixture-clock.ts`; реальный host проверил cookie и `X-Pocket: 1`.
4. Через реальные `/api/sessions` и `/api/c/:id/configure` созданы два разговора с общим cwd и моделью `fixture/deterministic` из собственной временной `models.json`.
5. Модель получила настоящий список инструментов host и вызвала `clock`. HTTP provider отказывает, если просят выдать tool call, которого host не объявил. Результат инструмента попал в настоящую историю; затем модель ответила `HOST_FIXTURE_ACK`.
6. Это повторено для обоих разговоров: **4 deterministic HTTP requests**, **0 live LLM calls**. Официальный launcher штатно остановлен SIGINT; существующая пользовательская установка не затрагивалась.

Фактические conversation IDs — **3 и 23**, не `ROOT_CONVERSATION_ID = 1`. Это важная интеграционная граница: общий Pocket Harness имеет несколько пользовательских разговоров, и actor нужно связывать с его точным ID, не с общей константой root.

Доказательства: [pocket-deterministic-smoke.json](../tests/host/evidence/pocket-deterministic-smoke.json), [реальный process log](../tests/host/evidence/pocket-real-process.log), [первый CLI/auth smoke](../tests/host/evidence/pocket-cli-start.log). Provider имеет отдельные 3/3 unit checks — [provider-unit.log](../tests/host/evidence/provider-unit.log); они не заменяют реальные host проверки.

## Публичный Native source: проверенная альтернатива

Публичный Pi v1.0.2 действительно содержит experimental `cli.ts server/client`, Chord plugin bundles и worker-owned Harness. В изолированной среде запущен официальный server; его собственный example plugin загружен в двух разных session workers. Настоящий удалённый `ExampleFacetService.greet` вернул marker и activation count 1. Реальный `AgentController.prompt/waitForPrompt` сделал **2 localhost deterministic model requests** и получил ACK в обоих разговорах.

Доказательство: [public-host-smoke.json](../tests/host/evidence/public-host-smoke.json), [официальный client probe](../tests/host/evidence/public-client-smoke.log), [server log](../tests/host/evidence/public-server-deterministic.log).

Это не выбранный обход для DeLM. В этом публичном host `createCodingRegistry` закрыт внутри worker, session facets получают сервисы, но не API установки Durable tools/tasks. `AgentPromptRequest` имеет только message/images, без стабильного request ID. Обычный controller делает прямой SDK submit: частный Hindsight admission **не является обязательным свойством этого host**. Реальные ограничения другие — registry seam и idempotent input control.

В публичном Pi v1.4.0 (`4a080252f06caf63a525d7873c5d94d3c23887e0`) experimental server удалён; остался source-resolver. Это проверено по публичному дереву, не выведено из старого blocker report. Commit удаления: [7472cda0](https://github.com/earendil-works/pi/commit/7472cda0d6e51dfbf53c03f46b47aa42ac64bf64). Исторический experimental host нельзя выдавать за current ordinary Pi CLI.

Исходный архив v1.0.2: SHA256 `08a7f0eecbdf3115ca0d1b1643c7084f3d8758c2fd903fffc2ec15a2824ab35f`. Git snapshot не содержит generated model JSON. Для обычной source-сборки взяты только **43 JSON assets** из matching публичного pi-ai 1.0.2 tarball (SHA256 `8ac8e5fabd65e0f0ecb8538b6211824859f5997594005d7a03e1f70b38438a17`); официальный `check-model-data.ts` прошёл. Никакой host source не патчился.

Первый запуск child coordinator не наследовал test-only external dependency resolver и завершился ошибкой. Для исходников без новой npm-установки resolver передан только изолированным процессам через `NODE_OPTIONS`; официальный source resolver по-прежнему выбирает реальные workspace packages из публичного snapshot. Это module resolution, не подмена API, guard или scheduler. Прежние неудачные logs сохранены рядом; свежий provisioning/version smoke — в [discovery record](../tests/host/evidence/native-repro/public-host-discovery.json).

## Как повторить fixture

Из корня DeLM checkout. `POCKET_DEPS` — существующая `node_modules` поддержанного публичного Pocket 0.14.0, не папка private host и не личная конфигурация. Команды не устанавливают зависимости:

```bash
python3 -B tests/host/provision_pocket.py \
  --public-dependencies "$POCKET_DEPS" \
  --evidence-dir tests/host/evidence
```

Команда печатает JSON с `fixture` — путь к новому приватному locator вне проекта. Подставьте **именно напечатанный путь**, затем:

```bash
python3 -B tests/host/smoke_pocket.py --fixture "$FIXTURE"
python3 -B -m unittest discover -s tests/host -p 'test_provider.py' -v
```

Для повторной проверки bare public Native source используйте `provision_public_host.py --dependency-root EXISTING_PUBLIC_NODE_MODULES --evidence-dir OUTPUT`; `--dependency-root` повторяемый. Затем `smoke_public_server.py --fixture LOCATOR`. Исходники pin и generated JSON проверяются provisioning-кодом; источник не заменяется авторским wrapper.

Fixtures сохраняются приватно для следующего этапа. Они не являются новым продуктовым host, tracker, постоянным сервисом или копией чужой беседы. В публичном evidence нет owner token/cookie, содержимого авторских config/session или абсолютного домашнего пути автора. Процессы, запущенные smoke-командами, штатно закрываются.

## Граница следующей приёмки

- Продуктовый Pocket bridge, tool/task registration и настоящие host guards проверяет Bob; launcher/input lifecycle — Carol; bundled board/config/package — Alice.
- HOST-05 должен проверить **сам DeLM**, не этот clock demo, включая exact/work, replay/wrong bindings, две стороны event wake/read/ACK, stop/reopen/reload, несданный draft и удаление без потери данных.
- Alice/Carol независимо проверяют этот fixture/harness на крупной вехе. Автор не объявляет собственную fixture независимым финальным доказательством.
- Существующая MIT-публикация и исторические отчёты сохранены. Новые изменения не закоммичены и не опубликованы. Live-model smoke не разрешён и не выполнен.

Hashes переданных fixture-файлов и отчёта: [fixture-candidate.json](../tests/host/evidence/fixture-candidate.json). Сам manifest не включает собственный hash.

Публичные источники: [Pocket v0.14.0 README](https://github.com/TannerMidd/pi-pocket/blob/v0.14.0/README.md), [drop-in контракт](https://github.com/TannerMidd/pi-pocket/blob/v0.14.0/docs/extensions.md), [public linked sessions](https://github.com/TannerMidd/pi-pocket/blob/v0.14.0/docs/extensions/linked-sessions.md), [Pi v1.0.2 official entry](https://github.com/earendil-works/pi/blob/v1.0.2/packages/coding-agent/src/experimental/cli.ts), [public worker runtime](https://github.com/earendil-works/pi/blob/v1.0.2/packages/coding-agent/src/experimental/session-worker.ts).
