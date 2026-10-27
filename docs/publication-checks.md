# Проверки публикации исходников

Владелец разрешил публичный `Diffuzmetall/pi-durable-delm` под MIT, Git init, commit, создание репозитория и push. GitHub Release, npm publish, установка зависимостей и вызовы моделей не выполнялись. Production Native gate остаётся BLOCKED.

## Изменения

Добавлены корневая MIT-лицензия и Git ignores. Обновлены repository/license metadata, документация и две проверки лицензии. `private:true` сохранён против случайного npm publish. Upstream notice и исполняемый runtime не изменены. Hash package.json обновлён в provenance; прежняя evidence сохранена как историческая, не как проверка нового commit.

## Свежие результаты

- Python core: 48/48; packaging: 5/5; launcher: 7/7; demo: 1/1. Все четыре unittest-команды завершились с exit 0.
- Все 29 текущих provenance hashes совпали, в том числе неизменённые upstream files.
- Предпубликационный список: 99 обычных файлов, 615916 bytes до добавления этого отчёта. Весь список получен через `git ls-files --others --exclude-standard`; `dist/`, dependencies и caches исключены. Окончательный manifest — дерево Git commit.
- Ограниченный content scan на распространённые форматы credentials/private keys, home-prefixes и email не нашёл секретов. Единственное совпадение private path — отрицательный `assertNotIn` в `tests/launcher/test_launcher.py`. Это не универсальная гарантия отсутствия секретов.
- Author/committer используют GitHub noreply identity владельца.
- `npm pack --ignore-scripts` из чистой копии публикуемых файлов: 97 files, SHA256 `a07c2ce675ce05eaf1bd2d6cf451a8085d9743adad6c83b957ae38461c6be63f`. Полная MIT включена, запрещённых путей и специальных tar members нет. Реальная установка этого payload, CLI `--help` и demo (`привет-мир`) завершились с exit 0. Это временный проверочный архив до добавления данного отчёта, не release asset и не hash Git commit.

## Сохранённая неудачная проба и ограничения

Первая сборка из рабочей папки после Python-тестов включила созданные subprocess-ами `__pycache__/*.pyc`: root `.npmignore` не исключил их внутри явно включённых `files` directories. Проверка содержимого корректно отказала до установки или публикации. Альтернатива — сборка из чистой копии Git-кандидата — прошла; caches в Git не входят. Для повторной упаковки используйте чистый checkout до тестов. Поведение npm ignore не исправлялось в рамках публикации исходников.

29 Node SDK/faux проверок и ordinary Pi discovery заново не запускались; их предыдущие результаты находятся в исторической приёмке. Новых claims о protected host admission, живых моделях или сохранении editor draft нет. Старые локальные `dist` archives/manifests не публикуются.
