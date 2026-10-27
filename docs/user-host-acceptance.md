# Приёмка DeLM у существующего Native host — HOST-05

## Результат и границы

**Установленный DeLM прошёл локальную проверку на совместимом настоящем Native Durable.** Host, его registry/Harness, owner, scheduler, guards, workers, storage и transport настоящие; детерминированный localhost HTTP заменяет **только модель**. Всего 39 HTTP-запросов, ноль живых LLM-вызовов. Продукт — только DeLM board/CLI, session facet, skill и observer; Native framework, Pocket, новый Harness и авторский runtime не поставляются.

Совместимость условна: публичный Native v1.0.2, commit `cd32f7725fdbddbaecdff5b1e68491563394e0ca`, **с отдельной явной трёхфайловой поправкой локального `DurableSession` API 1**. Это не неизменённый stock release. Source-копии находятся вне продукта и используются только как disposable тестовая платформа; source checkout не требуется обычному launcher. Host без этого API не поддержан: никаких разрешающих заглушек, второго владельца SQLite или автоматической установки другого host. [API и ограничения](native-compatibility.md).

Это фактическая самопроверка конечного milestone. Независимые решения существующих Alice/Carol и окончательная связь архива с этими данными фиксируются внешним `dist/HOST05-final-manifest.json`, чтобы не создавать самоссылочный hash. До этих решений готовность review-input не означает принятия всего HOST-05. Публикация/commit/push и эксплуатация пользовательского host этой проверкой не выполнялись.

## Какие байты проверены

- Исходный producer-архив: `8f5aed058020f10fe387260d8a5acf0cebe20f9b0773beff57113f147f4516f3`.
- Проверенный установленный архив: `4c7441af5851b13daa7dc43397256217a182f8242afef8e068704966f6b5178d`. Заменены только два тестовых файла: `tests/acceptance/check_artifact.py` и `tests/packaging/test_packlist.py`.
- **Все 34 runtime/license/source-map assets идентичны producer-архиву и текущему `provenance.json`.** Реальные Native сценарии исполняли JS facet, Python/vendor/CLI и исходные host helpers непосредственно из установленного version tree, не из исходной папки.
- Последняя оболочка с документацией, QA harness и очищенными доказательствами допустима только при полном равенстве этих 34 assets. Внешний final manifest перечисляет каждый файл и SHA, изменения оболочки и проверенную связь с установленным кандидатом. Изменение runtime потребует новой относящейся к нему проверки; старый результат не переносится автоматически.
- API patch SHA-256: `3460016c2130e2286ccd59c522b4318a2c13b0ad034dbb09f4e31776b23098ae`. Три изменённых публичных файла и их postimages проверены до копирования тестового source; прочие исходные файлы совпадают с pin.

## Свежая установленная компонентная проверка

[Машинный отчёт](evidence/user-host/artifact/acceptance.json) содержит 16 выполненных команд, их exit codes и архивный SHA. Это отдельная стадия, не свидетельство Native само по себе.

| Проверка из установленного payload | Результат |
|---|---|
| Install/repeat, переносимый bin, import closure внутри payload | PASS |
| Python core | 48 PASS |
| Packaging | 9 PASS, 1 SKIP: исходные `.npmignore` намеренно не входят в npm payload |
| Тот же build-only packlist test в source | 1 PASS; все шесть правил присутствуют |
| Launcher Python | 21 PASS |
| Unicode demo + CLI | PASS, `привет-мир` |
| Публичный SDK/faux + input tests | 31 PASS, 0 SKIP; это не настоящий host |
| Парсер обычного Pi | PASS отдельно, не подмена Native discovery |
| Полный doc-only update, rollback, повтор, отказ изменить пользовательский tree | PASS |
| Payload uninstall сохраняет изменённый tree/чужие файлы | PASS |

Публичные SDK/client модули версии 1.0.2 предоставлены внешним pinned test source resolver; опубликованные build dependencies уже существовали и использовались read-only. Обычный Pi parser использовал отдельное публичное дерево 1.4.0. Зависимости не устанавливались. Это честное условие тестовой среды, не проверка неизвестного размещения peers у любого пользователя. Обычная установка должна разрешать объявленные публичные пакеты штатно.

## Настоящий Native из установленного архива

Основной [result.json](evidence/user-host/installed-native/core/board-e2e/result.json) и [наблюдение реальных system prompt](evidence/user-host/installed-native/installed-native.json):

- 24 HTTP-запроса, два реальных worker-owned Native root и одна настоящая Python-доска/рабочая папка. Native Bash вызывает абсолютные actor-local CLI и пишет общий результат.
- Exact ALL-DONE не срабатывает после одного результата в ограниченном 400 ms окне; после обоих пробуждается правильный Bob, читает **тот самый сохранённый snapshot**, явно ACK и сверяет настоящий `delm_wait status`.
- Начальные два claim намеренно prebound для стабильных owner epochs; Bash их replay **не называется свежей конкуренцией**. Свежая конкуренция проверена ниже отдельно.
- Неподходящие session/workspace/instance, actor rebinding, тип и изменённый утверждённый payload отвергнуты; повтор того же request не дублирует ввод. Resume не создаёт dummy input.
- Реальный restart server/workers сохраняет pending wait и точные path/session/instance/wait IDs. Официальные presentation-build **и worker reload** сохраняют его; реальная owner `beforeTool` policy продолжает запрещать вызов после install/restart/reload.
- Настоящий OS PTY Native editor сохраняет несданный draft через reload и DeLM wake; Enter не отправлен, draft отсутствует в обеих историях.
- Available-work wake не назначает owner: snapshot read/ACK оставляет задачу open/unowned. Tool.cancel прекращает другой exact wait; исходный FACT-after-cancel — ограниченное доказательство, дополненное фактическим DONE ниже.

### Скилл обнаружил именно Native

До первого worker/model запроса атомарно создана стандартная project-local `.pi/skills/delm` symlink на установленный skill. Никакие глобальные skills/settings или discovery implementation не подменялись. **Во всех 24 настоящих model HTTP requests Native сам сформировал `<name>delm</name>` и действительный location установленного/project-local SKILL.md.** Наблюдатель проверяет вход только подменённой модели; в доказательствах сохраняет name/location и SHA system prompt, не полный prompt. Поле `pi.skills` и парсер обычного Pi не используются как замена этому наблюдению.

## Свежие claims, stop, отключение и удаление

[Lifecycle result](evidence/user-host/installed-native/lifecycle/result.json), настоящие client logs рядом:

1. Два Native Bash вызывают claim **новой unowned задачи** с исходной revision; Bob выигрывает, Alice теряет гонку, только победитель завершает задачу и пишет общий файл. Не fixture-preclaim и не соревнование восьми LLM.
2. При pending watcher настоящий `control.stop` приводит его в cancelled; последующие события и DONE не добавляют model work. Resume сам input не отправляет.
3. После реального `dispatchCommitted` и принятого wake уже начат model HTTP request. Тест держит **ответ модели**, не host/policy. Настоящий stop abort/waitForIdle возвращается **до освобождения ответа**. Поздний запрещённый ответ не появляется в Native history; непрочитанный receipt не ACKed автоматически. Ожидаемый BrokenPipe на fake HTTP endpoint — следствие фактической отмены запроса, не ошибка модели/host, замолченная как PASS.
4. Через настоящий публичный owner API на уже неактивных сессиях выбран прежний policy plugin **без DeLM**, не удалены другие guards. Удалена только точная созданная тестом skill symlink. Payload manager физически удалил всё чистое managed version tree и current link.
5. После удаления **без DeLM bytes/profile** открыты те же две Native сессии: прежние и свежие claim histories читаются, результат сохранён, owner policy v2 реально отвечает. Обычный Native prompt выполнился; в фактическом model request есть обычный `bash`, но нет `delm_wait` и DeLM skill. Hash обоих board SQLite файлов до/после совпал; unread receipt и user data не очищались.

Это 9 HTTP запросов supplemental + 1 уже после удаления. Test-only public dependency hook вынесен в disposable fixture до удаления: существующий тестовый Native после удаления не зависит от удалённых файлов DeLM. Собственные Native библиотеки/данные/настройки не удалялись.

### Tool.cancel, затем настоящий DONE

[Отдельный результат](evidence/user-host/installed-native/tool-cancel-done/result.json) закрывает точный замеченный peer-review пробел, не переименовывает FACT в DONE. После успешного удаления повторно установлен **тот же** архив; штатный owner profile снова подключил facet к прежним session/instance IDs. Оригинальный Bob wait, отменённый модельным `delm_wait cancel` в основном сценарии, всё ещё cancelled. Настоящий Native Alice через Bash впервые claim/complete его бывшую open/unowned dependency. Получено **2 producer HTTP, 0 consumer wake HTTP**, cancelled сохранён после реального DONE и ограниченного 500 ms наблюдения; обе беседы штатно остановлены. История не пересоздавалась.

## Обычный установленный launcher

[Результат и логи](evidence/user-host/installed-normal-launcher/result.json) получены новым запуском **поставленного** `tests/launcher/real_native_control.py` из отдельной чистой установки того же архива:

- Реальные публичные client APIs и явный Unix socket уже работающего Native. Product `--host-source` не передавался; host/source не устанавливались launcher.
- Ровно две точные сессии получили только свои bootstrap. Реально потерянный ответ после принятия input восстановлен тем же request; повтор start не добавил model work. Изменённый notify и потерянная recorded session отвергнуты, сессия не создана заново.
- Настоящие restart/resume сохраняют exact instances без dummy input. OS PTY draft пережил настоящий product notify, отсутствует в обеих историях, Enter не отправлен. Stop подтверждён.
- 3 детерминированных HTTP, 0 живых моделей. Тестовые public dependency aliases открыто указаны выше; это не обещание самоустановки Node peers.

## Ошибки самого QA и исправления

- Первоначальный installed packaging test требовал build-only `.npmignore`, хотя сам source packlist test требует не включать их в archive. Исправлен **тест**, не runtime: SKIP лишь когда отсутствуют **все шесть** правил; частичный source по-прежнему FAIL. Реальный source pack/cache test и независимая проверка всего payload остаются обязательными. Старая ошибка сохранена в `artifact/packaging-old-buildrule-missing.log`.
- Старый privacy scanner ошибочно считал явно замаскированный `<SANDBOX>/child/home/.pi` реальным домашним путём. Нормализуется только явный sandbox token; пять отрицательных/положительных assertions, включая разделители CSV/присваивания, оставляют незамаскированный home prefix запрещённым.
- Первый финальный envelope отвергнут настоящим privacy audit **до install**: argv обычного Pi probe содержал незамаскированный публичный dependency parent URI с домашним prefix. Исправлен logger для **точного синтетического** `__public_skill_probe__.mjs` URI и соответствующая старая запись argv; реальные пути не разрешены и scanner не ослаблен. Отвергнутый архив не считается поставкой; окончательный audit связан с новым hash во внешнем manifest.
- После успешно выполненных 9 запросов supplemental test ошибочно ожидал `packagePaths` в **высокоуровневом** `prepareSession` return. На деле это presentation data. Исправлен QA boundary; уже завершённые claims/models не повторялись: сохранённый exercise checkpoint восстановлен по фактическому успешному client result и trace после пройденных count/outcome assertions, продолжена только фаза removal. Итоговое отсутствие DeLM и наличие прежнего guard проверены фактически, а не формой ответа.

## Воспроизведение и непройденные границы

В `tests/acceptance/` находятся `check_artifact.py`, `check_native_installed.py`, `check_installed_lifecycle.py`, `check_cancel_done.py` и общий public-client probe. Передавайте **свой разрешённый disposable public fixture locator**, archive и evidence dir; ни личную установку, ни реальные беседы туда не направляйте. Полный порядок: component artifact → installed Native core → lifecycle/removal → reinstall/tool-cancel-DONE. Normal launcher запускался из другой чистой установки. Программа сохраняет приватные locator вне публикуемых доказательств.

`--resume-removal` нужен только после уже подтверждённого exercise checkpoint; не повторяет claims/models. После фактически завершённого removal не запускайте предыдущую стадию повторно ради «зелёного» лога. Сами QA файлы не становятся новым host/framework.

**NOT_TESTED / не заявляется:** живые LLM, model quality/latency/cost, восемь живых агентов, произвольная stock-версия Native/обычный Pi/Pocket, Windows, любые приватные пользовательские настройки и публикация нового release. Update/rollback проверяет полный payload с doc-only successor и неизменным runtime; это не доказательство совместимости любой будущей миграции данных или бинарного downgrade. Leases advisory; stop не доказывает завершение произвольного неподконтрольного shell-процесса. Эти границы не устраняются SDK PASS или исходным MIT-публикационным разрешением.
