# Локальная готовность к поставке

## Решение

**Исходники подготовлены к разрешённой владельцем публичной публикации в [Diffuzmetall/pi-durable-delm](https://github.com/Diffuzmetall/pi-durable-delm) под MIT.** Автономный payload и приёмочная документация готовы. Полный production-релиз Native **BLOCKED**: не подтверждён публичный host-контракт protected admission, discovery Durable registry adapter и управления точными сессиями. Выдавать локальную установку файлов за решение этого ограничения нельзя.

Исходный проект, работающий run/серверы/беседы, личный скилл, global settings и host не изменялись. При первоначальной локальной приёмке не создавались модели, удалённый репозиторий, commit, push или release; зависимости не устанавливались. Последующим прямым поручением владелец разрешил Git init, commit, создание публичного `Diffuzmetall/pi-durable-delm`, MIT и push. npm publish и GitHub Release не входят в это поручение.

## Что поставляется

| Путь | Назначение |
|---|---|
| `bin/delm`, `scripts/` | Установленный CLI, доска, domain/delivery/leases и observer |
| `vendor/DeLM/` | Семь закреплённых upstream files с полным MIT license |
| `extensions/delm/` | Публичный SDK-компонент, обязательная настоящая host admission capability |
| `skills/delm/` | Переносимый скилл, prepare/status/capabilities, input helper и справка |
| `prompts/`, `examples/slugify/` | Worker template и готовый Unicode-demo |
| `packaging/` | Управляемая локальная установка, update/rollback/uninstall |
| `tests/`, `docs/evidence/` | Scoped тесты, чистая приёмка, включая сохранённые неудачные пробы |
| `README.md`, `docs/`, notices, JSON maps | Пользовательская документация, происхождение и parity |

Локальные сборки находятся в `dist/` рядом с деревом. Они не вложены друг в друга. Канонический payload — `pi-durable-delm-0.1.0.tgz`; исходный непосредственно протестированный архив сохранён отдельно как `pi-durable-delm-0.1.0-tested.tgz`. Внешний `dist/final-manifest.json` содержит точный hash окончательного архива, список/хеш каждого файла и побайтовое соответствие 29 runtime entries проверенному архиву.

`dist/` исключён из Git: старые архивы и их manifests сохраняются только локально. Сохранённые ниже результаты `docs/evidence/` относятся к прежнему проверенному архиву, не к новому Git commit. Для публикации изменены лицензия, metadata, документация и проверки metadata; исполняемые runtime-файлы не менялись. `provenance.json` содержит актуальный hash package.json; старый hash остаётся в исторической evidence.

Readiness-report не включает собственный hash: это породило бы самоссылку. Его целостность фиксирует внешний manifest. После чистой приёмки разрешены только новые report/evidence/harness и metadata; изменения исполняемого продукта требуют новой соответствующей проверки.

## Проверенные действия

Точные команды приведены в [README](README.md); отдельная регистрация production Native **не заявлена**.

- **Собрать:** `npm pack --ignore-scripts --pack-destination "$OUT"`. Без установки зависимостей и публикации.
- **Установить:** извлечь `package/packaging/install.py` из tgz; `python3 install.py install "$ARCHIVE" --prefix "$PREFIX"`. Повтор возвращает `unchanged`; всегда `native_registered:false`.
- **Проверить CLI:** `"$PREFIX/current/bin/delm" --help`.
- **Demo:** из установленного корня `python3 -B -m unittest discover -s examples/slugify -v`, затем `python3 examples/slugify/slugify.py 'Привет, мир!'` → `привет-мир`.
- **Подготовить:** `skills/delm/Tools/Run.py prepare` с реальными разрешёнными AGENTS/plan/approved prompt; затем readonly `status`. Для начала список возможностей — `capabilities`.
- **Остановить:** backend в foreground через Ctrl+C; observer через `q`; участников отдельно штатным host control, если он доступен. Универсального рабочего auto stop/resume для stock Native сейчас нет.
- **Обновить/откатить/удалить:** операции `install`, `rollback`, `uninstall` того же bootstrap с тем же prefix. Rollback требует двух чистых управляемых версий. Изменённое дерево не перезаписывается, пользовательская история сохраняется.

Автоматические start/resume/notify/stop отказывают до побочных эффектов. Ни файл prompt, ни созданный RUN не доказывают фактический первый Native input. Сохранение настоящего несданного draft и доставка в живую модель в новой поставке не проверялись.

## Доказательства

[Независимая приёмка](docs/acceptance.md): **90/90 scoped тестов** из установленного артефакта на Linux x86_64, Python 3.13.7, Node 24.19.0. Из них 48 Python core, 5 packaging, 7 launcher Python, 1 demo и 29 Native/input-helper SDK-faux. Публичные Durable/pi-ai/chord — 1.4.0; ordinary Pi skill parser — 1.4.0; jiti — 2.7.0.

Реальные full-payload update/rollback, byte restoration, отказ обновления user-edited tree и uninstall с сохранением чужих файлов проверены. Ordinary Pi parser обнаружил delm без diagnostics; это **не** stock Native registry discovery. Тестовые 2/4/8 identities не равны восьми живым LLM.

Machine evidence и hashes логов: [acceptance.json](docs/evidence/acceptance.json). Первая ошибка выбора SDK 1.2.0 и ошибка смешанных parser dependencies сохранены и объяснены; не скрыты повторными зелёными прогонами. Реальный downgrade на прежний work-unaware Native runtime в новом artifact не проверялся. До такого отката обязательны drain/cancel work-watchers и reconciliation accepted inputs; payload rollback сам этого не делает.

## Происхождение и лицензии

| Категория | Факт |
|---|---|
| Original | Python DeLM commit `66617616e708758f91624e5cc03659732b82f6a6`; включённые vendor files неизменны, full MIT сохранён |
| Adapted | Python entry на bundled vendor root, Native adapter с явным host capability, универсальные skill/workflow материалы |
| New | Domain/delivery/leases и observer локальной адаптации; переносимый launcher/input binding, packaging, demo, документация и приёмочный harness |

«New» не означает, что прежний unpublished local-adaptation code написан заново в этом переносе. Точные source paths, source/package hashes и unchanged/adapted/written-here даны в [provenance.json](provenance.json); функции/тесты/границы — в [parity.json](parity.json).

Полный upstream copyright сохранён дословно: `Copyright (c) 2026-2027 Yuzhen Mao,` и `Azalia Mirhoseini`, вместе с полным [MIT permission text](vendor/DeLM/LICENSE). Наши отдельные части получили MIT по явному решению владельца, см. [LICENSE](LICENSE). `private:true` сохранён только как защита от случайной публикации в npm.

[Paper v3](https://arxiv.org/abs/2606.10662v3), [сайт авторов](https://yuzhenmao.github.io/DeLM/), [Python source](https://github.com/yuzhenmao/DeLM) и [отдельный продуктовый плагин](https://github.com/Decentralized-LM/delm-agent-plugin) разделены в [UPSTREAM](UPSTREAM.md) и [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md). PDF/media, research archive и Rust runtime продуктового плагина не поставляются; их показатели эффективности не выдаются за измерения этой адаптации.

## Content audit

Архив проверен по полному списку членов и содержимому: нет реальных RUN/config.json, Native SQLite, `.local/`, `.git/`, caches, bundled node_modules, скриншотов, conversation dumps, auth/provider settings или research media. Разрешены только обычные файлы/каталоги; runtime hashes и локальные Markdown links сверены.

Логи созданы заново на фиктивных данных; пути temporary installation и существующих public dependencies заменены маркерами. Единственный home-prefix literal в отрицательном privacy assertion теста явно классифицирован как deny-list, не путь runtime. Это ограниченный scan + source/content review, **не** универсальная гарантия отсутствия любых секретов; перед реальной публикацией владелец утверждает полный manifest.

## Что нужно для полного релиза

1. **Поддержанный публичный Native host adapter/API:** существующий registry, точные run/workspace/actor/session bindings, настоящая protected admission/context binding до submit, стабильный request ID/replay, безопасные reload/reopen/stop. Точное описание — [native-compatibility.md](docs/native-compatibility.md). Private symbol, новый владелец Native SQLite, FauxHost и allow-all не подходят.
2. **Решение владельца для GitHub принято:** публичный `Diffuzmetall/pi-durable-delm`, MIT, Git init/commit/create/push разрешены. Состав исходников — дерево репозитория без `dist/`, caches, dependencies и приватных данных; точный список фиксирует Git commit. Production gate остаётся отдельным; release assets и npm не публикуются.
3. После появления host capability — отдельная production-проверка discovery, initial delivery, exact resume/stop и draft preservation; источник/faux не заменяют её. Дополнительные модели или установки требуют отдельного разрешения.

Оригинальный PUB-08 остаётся заблокирован production Native gate. Публикация исходников по отдельному поручению владельца не закрывает его и не является production-релизом Native.
