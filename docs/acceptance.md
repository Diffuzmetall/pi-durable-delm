# Независимая приёмка локальной поставки 0.1.0

## Вердикт

**LOCAL ARTIFACT PASS / PRODUCTION NATIVE BLOCKED.** Автономный payload устанавливается из собранного архива и проходит проверки без импортов исходного проекта или личного скилла. Это не turnkey-релиз Native: публичный контракт host admission, registry discovery и управления сессиями всё ещё не подтверждён.

Проверял существующий участник Dave, отдельно от авторов Python-ядра, Native-компонента, launcher и установщика. Собственная документация не выдаётся за независимое ревью. Новые модели, зависимости и сервисы исходного запуска не добавлялись; действующие беседы и несданный draft не затрагивались.

## Что именно проверено

Входной замороженный архив: `pi-durable-delm-0.1.0.tgz`, **74 файла**, SHA256:

```text
942d10bc780ceb06da40ec7ff6e612e203dea222028a362a8388276f97800e96
```

Архив получен от упаковщика после исправления binding input. В нём helper `skills/delm/Tools/NativeInput.mjs` имеет SHA256 `7f68b45ee94248c386161cbdedd8573054fcc5a00ceefec6bd0813cce002943c`. Все 29 записей runtime SourceMap сверены с реальными байтами архива и установки.

Тесты исполнялись из распакованного управляемого version tree, в новом временном HOME и cwd вне исходного проекта. `PYTHONPATH`, личная конфигурация, авторизация и переменные прежнего Native-сеанса не наследовались. Все загруженные Python-модули доски подтверждены внутри установленного payload. Исходный checkout физически остаётся на машине; это не контейнерный запрет доступа к нему и не утверждение, что он был удалён.

После добавления этого отчёта и приёмочного harness меняется только оболочка поставки. Итоговый `dist/final-manifest.json` снаружи архива связывает новый artifact SHA и hash каждого включённого файла с проверенными runtime-байтами. Он не включён в собственный архив, чтобы избежать самоссылочного hash. Отчёт не приписывает новым документационным байтам старый hash архива.

## Среда

| Компонент | Проверено |
|---|---|
| OS | Linux x86_64 |
| Python | 3.13.7 |
| Node | 24.19.0 |
| npm для сборки | 11.17.0 |
| Публичные Durable / pi-ai / chord | 1.4.0, каждый |
| Публичный ordinary Pi parser | pi-coding-agent 1.4.0 |
| Reload dependency | jiti 2.7.0 |

Использованы уже установленные **публичные package exports**, не приватный host или global-runtime shim. Новые зависимости не устанавливались. Другие версии Python/Node, Windows и macOS не проверялись; нижняя граница Node из package metadata не равна тестированию каждой версии выше неё.

## Результаты из установленного артефакта

| Проверка | Результат | Доказательство |
|---|---|---|
| Bootstrap installer извлечён из tgz; install → повторный install | PASS; `installed` → `unchanged`, `native_registered:false` | `evidence/install.log`, `repeat-install.log` |
| Installed `bin/delm` и полное Python-ядро | PASS, 48/48 | `installed-bin.log`, `python.log` |
| Packaging guards, managed hashes и SourceMap | PASS, 5/5 | `packaging.log` |
| Portable launcher, точные approved inputs, 2/4/8, реальный HTTP status | PASS, 7/7 | `launcher-python.log` |
| Unicode-demo и CLI | PASS, 1/1; `привет-мир` | `demo.log`, `demo-cli.log` |
| Пять scoped Native suites + input helper | PASS, 29/29 | `native-sdk-faux.log` |
| Обнаружение delm публичным ordinary Pi skill parser | PASS; одна skill, без diagnostics | `skill-discovery.log` |
| Python import closure | PASS; только установленный payload | `import-closure.log` |
| Полный payload update → rollback | PASS; прежние файлы восстановлены побайтно | `update.log`, `rollback.log` |
| Update изменённого дерева | PASS: отказ до перезаписи | `refuse-edited-update.log` |
| Uninstall | PASS; пользовательский файл и неуправляемая история сохранены | `uninstall.log` |
| Stock Native registry discovery / protected admission / auto start-resume-stop | **BLOCKED / NOT VERIFIED** | [Native compatibility](native-compatibility.md) |
| Реальные модели, живой editor draft, восемь живых LLM | **NOT TESTED** | Модели не запускались, draft не отправлялся |
| Реальный downgrade на work-unaware Native predecessor | **NOT TESTED** в новой поставке | Новый artifact не содержит прежний runtime; [обязательные условия отката](operations.md) сохраняются |

Итого **90 проходящих scoped тестов**: 48 + 5 + 7 + 1 Python и 29 Node. Это новые результаты установленного артефакта, не baseline исходной папки. Предупреждения Python ResourceWarning сохранены в логах и не скрыты.

Native/faux проверки используют настоящий scheduler, SQLite и HTTP/CLI на фиктивных данных. Они охватывают exact ALL-DONE, work availability/recheck/competition/handoff, отсутствие wake на FACT/unready, root/actor/workspace guards, отказ admission, compact reference/pending/read/ACK, cancel/retry/reopen/response loss и 4/8 identities. Отдельные input-helper проверки отвергают изменённый корректно хешированный input под прежним request ID после reopen, а неизменённый replay не повторяет admission.

Это не утверждение, что тестовая admission-заглушка представляет production policy. Публичный adapter без настоящей host capability отказывает; ordinary Pi skill parsing не доказывает загрузку Durable registry adapter.

## Неудачные пробы и их разбор

Сначала приёмочный harness ошибочно выбрал существующий **SDK 1.2.0**, а не заявленный 1.4.0: Node получил **20/29 PASS, 9 FAIL** из-за несовместимого SQLite status constraint. Сохранён `native-sdk-unsupported-1.2.log`. После проверки версий выполнен только затронутый Node-набор на уже установленном публичном 1.4.0: **29/29 PASS**. Неизменившиеся проходящие Python suites повторно не запускались.

Попытка ordinary Pi parser через dependency override Durable SDK смешала две разные dependency trees и упала на отсутствующем export. `skill-discovery-mixed-dependencies.log` сохранён. Правильная проверка использовала собственное публичное ordinary Pi export-resolution без Durable hook; delm обнаружен. Воспроизводимый harness проверяет peer versions заранее и разделяет эти деревья.

Статический scanner сначала принял отрицательную privacy-проверку `assertNotIn` в launcher test за ссылку на частную установку. Это deny-list literal, не runtime dependency. Классификация явно записана в `evidence/acceptance.json`; остальные строки и файлы проверяются без этого исключения. Это ограниченный content scan и ручное ревью, не универсальный secret scanner или сертификат отсутствия любых персональных данных.

## Воспроизведение

Из корня поставки после ручной проверки prerequisites:

```bash
python3 -B tests/acceptance/check_artifact.py \
  --archive dist/pi-durable-delm-0.1.0.tgz \
  --evidence-dir docs/evidence
```

`dist` — каталог локальной сборки рядом с исходным деревом, не вложенный архив внутри payload. Если tgz получен отдельно, передайте его реальный путь. В самом payload находится harness, но не копия собственного tgz.

При public dependencies вне локального `node_modules` задайте `DELM_TEST_NODE_MODULES` списком существующих node_modules roots в нужном порядке. **Первое найденное дерево каждого Durable peer должно содержать 1.4.0.** Для отдельной установки ordinary Pi задайте `DELM_TEST_PI_MODULES` её node_modules root: skill parser исполняется без Durable resolver hook. Никаких путей машины автора в пакете нет; эти значения выбирает проверяющий.

Harness сохраняет чистый временный HOME для диагностики, перехватывает логи и проверяет сохранение user edits/run data. Не направляйте `--evidence-dir` в чужие файлы. Состояние тестовой среды не является живым RUN пользователя. Без public dependencies тест должен отказать на prerequisites, а не устанавливать их сам или объявлять Native PASS.

Машинные результаты, hashes логов и ограничения: [evidence/acceptance.json](evidence/acceptance.json). Parity: [parity.json](../parity.json). Происхождение: [provenance.json](../provenance.json). Это историческая приёмка прежнего локального архива: её hashes не относятся к новому Git commit. Впоследствии владелец разрешил публичные исходники под MIT; metadata и проверки лицензии обновлены. Production host capability остаётся отдельным незакрытым gate; локальный PASS и публичный GitHub его не заменяют.
