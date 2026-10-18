{
  config,
  lib,
  osConfig,
  ...
}:
let
  brew = osConfig.homebrew.prefix;
  # These formulae are intentionally not linked into Homebrew's bin directory.
  preferredPaths = map (name: "${brew}/opt/${name}/bin") [
    "curl"
    "libpq"
    "postgresql@18"
    "openjdk@17"
  ];
  brewInit = ''
    if [[ -x ${brew}/bin/brew && ( ''${HOMEBREW_PREFIX-} != ${lib.escapeShellArg brew} || ":$PATH:" != *":${brew}/bin:"* ) ]]; then
      eval "$(${brew}/bin/brew shellenv zsh)"
    fi
  '';
in
{
  home = {
    sessionVariables = {
      EDITOR = "vim";
      VISUAL = "vim";
      NVM_DIR = "${config.home.homeDirectory}/.nvm";
      JAVA_HOME = "${brew}/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home";
      PLANTUML_JAR = "${brew}/opt/plantuml/libexec/plantuml.jar";
      GOPROXY = "https://proxy.golang.org";
      NODE_USE_SYSTEM_CA = "1";
      OPENCODE_DISABLE_DEFAULT_PLUGINS = "true";
    };
    sessionPath = preferredPaths ++ [
      "${brew}/bin"
      "${brew}/sbin"
      "/Library/TeX/texbin"
      "${config.home.homeDirectory}/go/bin"
      "${config.home.homeDirectory}/.local/bin"
    ];
    activation.createNvmDirectory = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run mkdir -p "${config.home.homeDirectory}/.nvm"
    '';
  };
  programs.zsh = {
    enable = true;
    defaultKeymap = "emacs";
    enableCompletion = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;
    # Login environment; interactive shells also have a guarded fallback below.
    profileExtra = brewInit;
    oh-my-zsh = {
      enable = true;
      theme = "simple";
      extraConfig = ''
        COMPLETION_WAITING_DOTS="true"
      '';
      plugins = [
        "git"
        "docker-compose"
        "tmux"
      ];
    };
    shellAliases = {
      ls = "eza --icons=always";
      python = "python3";
      dps = "docker ps";
      dpsa = "docker ps -a";
      k = "kubectl";
      h = "helm";
    };
    history = {
      path = "${config.home.homeDirectory}/.zsh_history";
      size = 100000;
      save = 50000;
      ignoreDups = true;
      ignoreAllDups = false;
      ignoreSpace = true;
      findNoDups = true;
      expireDuplicatesFirst = true;
      # Append immediately; zsh does not support combining this with shared history.
      extended = true;
      append = true;
      share = false;
    };
    setOptions = [
      "INC_APPEND_HISTORY"
      "NO_INC_APPEND_HISTORY_TIME"
      "HIST_VERIFY"
      "INTERACTIVE_COMMENTS"
    ];
    initContent = lib.mkMerge [
      # Before compinit/Oh My Zsh: complete Brew commands and deduplicate PATH.
      (lib.mkOrder 500 ''
        ${brewInit}
        path=(${lib.escapeShellArgs preferredPaths} $path)
        if [[ -d ${brew}/share/zsh/site-functions ]]; then
          fpath=(${brew}/share/zsh/site-functions $fpath)
        fi
      '')
      # After framework/history setup, before syntax highlighting wraps widgets.
      (lib.mkOrder 1000 ''
        bindkey '\e\e[C' forward-word
        bindkey '\e\e[D' backward-word
        bindkey '^[[1;3C' forward-word
        bindkey '^[[1;3D' backward-word

        # Keep startup predictable: use Brew's Node until an explicit `nvm use`.
        if [[ -r ${brew}/opt/nvm/nvm.sh ]]; then
          source ${brew}/opt/nvm/nvm.sh --no-use
          if [[ -r ${brew}/opt/nvm/etc/bash_completion.d/nvm ]]; then
            source ${brew}/opt/nvm/etc/bash_completion.d/nvm
          fi
        fi
        if (( $+commands[zoxide] )); then
          eval "$(zoxide init zsh)"
        fi
      '')
      (lib.mkOrder 1150 ''
        if [[ -r ${lib.escapeShellArg "${config.xdg.configHome}/macbook-nix/private-env.sh"} ]]; then
          source ${lib.escapeShellArg "${config.xdg.configHome}/macbook-nix/private-env.sh"}
        fi
      '')
    ];
  };
}
