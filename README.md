# MacBook configuration

Одна конфигурация `macbook`: nix-darwin задаёт настройки macOS, Home Manager — личное окружение и dotfiles, Homebrew — программы. Список пакетов хранится только в [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix).

## Установка

Нужны Command Line Tools (`xcode-select --install`), [multi-user Nix](https://nixos.org/download/) и [Homebrew](https://docs.brew.sh/Installation). После их установки открыть новый Terminal и проверить:

```sh
command -v nix brew git make
```

Склонировать репозиторий в удобную папку. Её расположение на конфигурацию не влияет:

```sh
git clone https://github.com/ythosa/macbook-nix.git
cd macbook-nix
```

Перед применением проверить три места:

- [flake.nix](flake.nix): `machine.username` должен совпадать с `id -un`. Значение по умолчанию — `ythosa`. `machine.system` — `aarch64-darwin` для Apple Silicon. Учётная запись уже должна существовать в macOS.
- [home/git.nix](home/git.nix): личные имя и почта Git. Они не зависят от логина macOS и папки репозитория.
- [modules/darwin/macos.nix](modules/darwin/macos.nix): предпочтения macOS. Сейчас выбраны `Europe/Moscow`, тёмная тема и выключенный application firewall.

```sh
make check
make setup
```

`setup` — короткое имя `switch`. Команда собирает систему, сверяет выбранного пользователя с текущим логином и запрашивает sudo для активации. Программы устанавливаются штатным модулем Homebrew во время активации; отдельный установщик поверх него не нужен. После завершения открыть новое окно Terminal.

Текущий nixpkgs не поддерживает Intel Mac: [поддержка `x86_64-darwin` удалена в 26.11](https://nixos.org/manual/nixpkgs/unstable/release-notes#x86_64-darwin-26.11). Для Intel нужен согласованный набор более старых nixpkgs, nix-darwin и Home Manager; одной смены `machine.system` недостаточно.

Если загрузка приложения прервалась, часть системных изменений уже могла примениться. Устранить причину, выполнить `make apps`, затем повторить `make switch`.

## Команды

| Команда | Действие |
| --- | --- |
| `make` / `make check` | Тесты подготовки активации и проверка вычисления flake без сборки |
| `make build` | Сборка без применения; результат доступен через `result` |
| `make setup` / `make switch` | Сборка и активация macOS, dotfiles и Brew-программ |
| `make apps` | Только установка недостающих Brew-программ |
| `make apps-check` | Проверка наличия Brew-программ без установки |
| `make brewfile` | Генерация локального `Brewfile`; файл исключён из Git |
| `make fmt` | Форматирование Nix-файлов; нужен `rg` из ripgrep |
| `make update` | Обновление Nix-зависимостей в `flake.lock` |

Все команды выполняются из корня репозитория. Кроме `update`, Nix-команды запрещают изменение lock-файла. Флаги `nix-command` и `flakes` передаются автоматически. Проверки и сборка могут обращаться к сети.

После редактирования настроек выполнить `make check`, затем `make switch`. Новые файлы сначала добавить через `git add`: [Git-flake использует только отслеживаемые файлы](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-flake#types).

## Структура

| Файл | Что менять |
| --- | --- |
| [flake.nix](flake.nix) | Логин, архитектура, подключение модулей |
| [modules/darwin/nix.nix](modules/darwin/nix.nix) | Nix и системная интеграция shell |
| [modules/darwin/macos.nix](modules/darwin/macos.nix) | Dock, Finder, trackpad, язык и firewall |
| [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix) | Программы, шрифты и taps |
| [home/default.nix](home/default.nix) | Личные модули и настройки текущего пользователя macOS |
| [home/shell.nix](home/shell.nix) | zsh, PATH, история, aliases и NVM |
| [home/git.nix](home/git.nix) | Имя, почта и aliases Git |
| [home/runtime-configs.nix](home/runtime-configs.nix) | Правила установки файлов из [dotfiles/](dotfiles/) |
| [scripts/switch.py](scripts/switch.py) | Безопасная подготовка после установщика Nix и запуск активации |

Чтобы добавить программу, достаточно одной записи в `homebrew.nix`. Чтобы разделить настройки по смыслу, добавить обычный Nix-модуль в `imports`. Дополнительные профили для одинакового окружения на другом Apple Silicon Mac не нужны: достаточно изменить логин.

Home Manager получает логин и домашнюю папку из nix-darwin. Пути к Brew вычисляются из `homebrew.prefix`, пользовательские — из настроек Home Manager. Системные пути macOS и абсолютные пути Nix store необходимы для работы; путей к конкретной копии репозитория в конфигурации нет.

## Как работают dotfiles

| Способ установки | Конфиги | Где редактировать |
| --- | --- | --- |
| Ссылки Home Manager | zsh, Git, clang-format, AeroSpace, Alacritty с темой, k9s с Dracula, Vim | В репозитории, затем `make switch` |
| Копирование отсутствующих файлов | Neovim, btop, tmux, VS Code | В домашней папке; для переноса на другой Mac скопировать правки обратно в `dotfiles/` |

Существующие обычные файлы на месте управляемых ссылок сохраняются с суффиксом `.before-home-manager`. Если резервная копия уже существует, Home Manager остановится, чтобы не затереть её. Не включать `force` для обхода конфликта без сравнения файлов: это [отключает защиту локальных правок](https://nix-community.github.io/home-manager/usage/dotfiles.html).

Редактируемые копии создаются после установки управляемых ссылок. Существующий файл или ссылка, включая сломанную, не заменяются. Это позволяет btop и Neovim сохранять настройки. Для повторной установки конкретного конфига закрыть приложение, сохранить его копию и освободить только соответствующий путь, затем выполнить `make switch`.

Файлы Neovim подхватываются рекурсивно, кроме `LICENSE`. k9s использует стандартную папку macOS `~/Library/Application Support/k9s/` и сам выбирает папки для своих данных. Стиль clang-format устанавливается в `~/.clang-format` и действует для исходников внутри домашней папки, если ближе к проекту нет собственного стиля; форматтер из Command Line Tools вызывается через `xcrun clang-format`.

Конфиг сам по себе не устанавливает приложение: например, Alacritty сохранён в dotfiles, но отсутствует в списке пакетов.

Новая утилита свободно создаёт свои конфиги рядом с управляемыми файлами. Они не попадут в Git автоматически. Чтобы переносить их на другие устройства, сохранить нужные файлы в `dotfiles/` и добавить правила установки в `runtime-configs.nix`. Кэши, историю, ключи и данные приложений туда не копировать.

## Shell и личные данные

Home Manager формирует startup-файлы zsh: окружение задаётся отдельно от интерактивных aliases, completion и подсветки. Brew и NVM подключаются с проверкой наличия; `nvm --no-use` оставляет Node из Brew до явного `nvm use`. Для переходов через zoxide доступны `z` и `zi`, обычный `cd` сохранён.

История содержит до 100000 записей в памяти и 50000 на диске. Команды сразу дописываются с timestamps; `SHARE_HISTORY` отключён, поскольку [он несовместим с `INC_APPEND_HISTORY`](https://zsh.sourceforge.io/Doc/Release/Options.html#History). Новые записи других окон можно прочитать через `fc -RI`.

Приватные переменные подключаются из `macbook-nix/private-env.sh` внутри `config.xdg.configHome` — по умолчанию `~/.config`. Файл хранить вне репозитория с правами `600`. Отслеживаемые файлы flake копируются в Nix store, поэтому секреты в Nix-выражения и dotfiles не добавлять.

Git использует личную identity для всех репозиториев, без правил для конкретной папки и без принудительной замены HTTPS на SSH. Локальные настройки Git могут иметь приоритет: проверить через `git config --show-origin --get user.email`.

## Что восстанавливается отдельно

Входы в аккаунты, лицензии, SSH-ключи, разрешения macOS, версии Node в NVM, глобальные npm/Go-инструменты, расширения VS Code и данные приложений не входят в эту конфигурацию. Colima устанавливается без собственного конфига и без переноса виртуальных машин. Reduce Motion при необходимости включить в System Settings → Accessibility → Motion.

Плагины Vim устанавливаются через Vundle:

```sh
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
vim +PluginInstall +qall
```

Если Vundle уже установлен, достаточно второй команды. Без плагинов тема Embark недоступна.

Плагины tmux устанавливаются через TPM:

```sh
git clone https://github.com/tmux-plugins/tpm.git ~/.tmux/plugins/tpm
~/.tmux/plugins/tpm/bin/install_plugins
```

Если TPM уже установлен, достаточно второй команды. После установки перечитать конфиг через `tmux source-file ~/.tmux.conf`. Плагин темы теперь называется PowerKit; в конфиге явно выбрана Tokyo Night, чтобы не зависеть от его стандартной темы.

## Обновление, конфликты и откат

Зависимости Nix зафиксированы в `flake.lock` и разделяют один nixpkgs через `follows`; Home Manager использует системный `pkgs`. Это соответствует [официальной схеме интеграции](https://nix-community.github.io/home-manager/nix-flakes/nix-darwin.html). Для обновления выполнить `make update`, просмотреть дифф lock-файла, проверить и применить конфигурацию. `system.stateVersion` и `home.stateVersion` задают совместимость, при обычном обновлении их оставляют прежними.

Brew-программы и плагины Vim/tmux не фиксируются lock-файлом Nix. Автообновление, общий upgrade и удаление сторонних пакетов при активации отключены. Обычное связывание пакетов, включая keg-only, оставлено Homebrew. Обновление выполняется явно, например `brew upgrade tmux`; установка новой программы может также изменить её зависимости.

Удаление записи из Nix прекращает установку пакета, но не удаляет установленную копию. Для удаления использовать `brew uninstall имя` или `brew uninstall --cask имя`.

Системный `zshrc` остаётся macOS. При переходе со старой версии его ссылка на прежний файл Nix заменяется обычным файлом с тем же содержимым. Обёртка активации автоматически сохраняет только точную стандартную правку `bashrc` установщиком Nix при наличии совпадающей исходной копии; остальные конфликты оставляет проверкам nix-darwin. Для предварительного просмотра этой подготовки:

```sh
make build
/usr/bin/python3 scripts/switch.py
```

Это не полный просмотр системных изменений. При `Unexpected files in /etc` сравнить перечисленные файлы и сохранить нужные версии перед повторной активацией. При ошибке `.before-home-manager` сначала сравнить существующую резервную копию и текущий файл.

Служебные пользователи `_nixbld*` и группа `nixbld` нужны для изолированных сборок multi-user Nix. Они не являются профилями настройки Mac.

Посмотреть поколения и откатить системную конфигурацию:

```sh
/run/current-system/sw/bin/darwin-rebuild --list-generations
sudo /run/current-system/sw/bin/darwin-rebuild switch --rollback
```

Откат возвращает поколение Nix. Программы Brew, редактируемые копии конфигов и данные приложений он не восстанавливает; удалённые настройки macOS также не обязательно возвращаются к прежним значениям.

Для дальнейших изменений: [рекомендации nix.dev](https://nix.dev/guides/best-practices.html), [модули Nix](https://nix.dev/tutorials/module-system/deep-dive.html), [параметры nix-darwin](https://nix-darwin.github.io/nix-darwin/manual/).
