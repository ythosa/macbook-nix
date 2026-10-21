{
  programs.git = {
    enable = true;
    package = null;
    includes = [ { path = "~/.config/git/identity"; } ];
    settings = {
      core.editor = "vim";
      user.useConfigOnly = true;
      alias = {
        co = "checkout";
        last = "rev-parse --short HEAD";
        br = "branch";
        ci = "commit";
        st = "status";
      };
      url."git@github.com:".insteadOf = "https://github.com/";
      url."ssh://git@".insteadOf = "git://";
    };
  };
}
