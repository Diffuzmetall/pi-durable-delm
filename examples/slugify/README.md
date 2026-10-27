# Маленький Unicode-пример

Проверить пример без моделей и сторонних зависимостей:

```sh
cd examples/slugify
python3 -m unittest discover -s . -v
python3 slugify.py 'Привет, мир!'
# привет-мир
```

Для подготовки shared-run скопируйте **этот небольшой пример**, а не чужой живой проект, в свою временную рабочую папку. `AGENTS.md` и `PLAN.md` уже включены. Путь RUN выбирается вне этой папки. Из installed package root команда подготовки Python-доски:

```sh
python3 scripts/delm_local.py init /tmp/slugify-run \
  --shared-workspace /absolute/path/to/your/slugify-copy --n 2 \
  --plan /absolute/path/to/your/slugify-copy/PLAN.md \
  --task 'Проверьте Unicode API и расширьте тесты в общем checkout по PLAN.md'
```

Выберите свежий RUN: существующий каталог init не перезаписывает. Эта команда создаёт артефакты, **не запускает модели и не доставляет input**. Реальный Native/skill launch выполняется только отдельно разрешённым поддержанным способом из главного README. При недоступном публичном admission контракте нельзя выдавать faux smoke за настоящий защищённый запуск.

Разница с исследовательским isolated-примером: здесь участники видят одни файлы и собирают один результат. Для independent/isolated legacy режима CLI остаётся совместимым, но переносить apply-протокол в shared checkout нельзя. Это demo функциональности, не benchmark скорости/качества агентов.
